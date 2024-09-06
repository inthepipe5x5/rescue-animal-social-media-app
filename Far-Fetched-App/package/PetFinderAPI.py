import os
from dotenv import load_dotenv
import datetime
import pytz
from dateutil import parser
import pycountry
import pandas as pd
from flask import json
from ratelimit import limits, RateLimitException
from petpy import Petfinder
import requests

# from ..models import User, UserAnimalPreferences  # , #UserPreferences

load_dotenv()


class PetFinderPetPyAPI:
    """
    API class with methods to store access PetFinder API and help functions to map user preference data to API search parameters
    """

    BASE_API_URL = os.environ.get("PETFINDER_API_URL", "https://api.petfinder.com")
    if "https://" not in BASE_API_URL:
        BASE_API_URL = "https://" + BASE_API_URL

    # store default user_preference
    default_options_obj = {
        "location": "ON,CA",
        "state": "ON",
        "country": "CA",
        "animal_types": [
            "dog"
        ],  # 8 possible values:  ‘dog’, ‘cat’, ‘rabbit’, ‘small-furry’, ‘horse’, ‘bird’, ‘scales-fins-other’, ‘barnyard’.
        "sort": "distance",
        "return_df": False,
        # "custom": False
    }

    animal_emojis = {
        "dog": "🐶",
        "cat": "🐱",
        "rabbit": "🐰",
        "small-furry": "🐹",
        "horse": "🐴",
        "bird": "🐦",
        "scales-fins-other": "🦎",
        "barnyard": "🐄",
    }

    def __init__(self, get_anon_preference_func, get_user_preference_func):
        self.petpy_api = Petfinder(
            key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET")
        )

        # utilizing dependency injection here to prevent circular imports from app.py, form.py, helper.py and this file
        self.get_anon_preference = get_anon_preference_func
        self.get_user_preference = get_user_preference_func

    def create_custom_url_for_api_request(self, endpoint, request_url, **params):
        """Create a url to make an API request based off passed in params object.


        GET https://api.petfinder.com/v2/{CATEGORY}/?{parameter_1}={value_1}&{parameter_2}={value_2}

        Args:
            category (str): category of API to be called on eg. animal, animals, organization, organizations
            action(str): what REST request to make on API eg. 'get' = GET request
            params (OBJECT {str:str}): params Python OBJECT will be iterated on to create the key:value string queries to the url separated by question marks eg. `?{parameter_1}={value_1}`
        """
        # handle if no params passed in
        params = {} if not params else params
        # handle if no request_url passed in
        request_url = (
            f"{self.BASE_API_URL}/v2/{endpoint}" if not request_url else request_url
        )

        # Obtain the current access token within the self.petpy_api class
        access_token = self.petpy_api._auth

        # Make a request to the specified endpoint with the access token
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(request_url, headers=headers, params=params)

        # Check for a successful response
        response.raise_for_status()
        return {
            "access_token": access_token,
            "results": response[endpoint].json(),
            "pagination": response["pagination"].json(),
        }

    def create_filter_conditions(self, preferences):
        """
        Create filter conditions based on a nested object of boolean or list values.

        Args:
        preferences (dict): A nested dictionary of preferences.

        Returns:
        dict: A dictionary of lambda functions to be used as filter conditions.
        """
        filter_conditions = {}

        attribute_keys = [
            "spayed_neutered",
            "house_trained",
            "declawed",
            "special_needs",
            "shots_current",
        ]
        environment_keys = [
            "child_friendly",
            "dogs_friendly",
            "cats_friendly",
        ]

        def create_list_condition(filter_key, filter_value):
            """
            Create a condition function for a list type preference.

            Args:
            filter_key (str): The key in the object to filter.
            filter_value (list): The list of acceptable values.

            Returns:
            function: A lambda function representing the filter condition.
            """

            def list_condition(obj_to_filter):
                obj_value = obj_to_filter.get(filter_key, [])
                if isinstance(obj_value, list):
                    # handle if obj_value is empty list
                    if obj_value and len(obj_value) > 0:
                        # Check if any of the filter values are in the object's list
                        return any(
                            target_item.lower() in nested_item.lower()
                            for nested_item in obj_value
                            for target_item in filter_value
                        )
                elif isinstance(obj_value, dict):
                    # If the object value is a dictionary, check for any matching items
                    return any(
                        any(
                            target_item.lower() in val.lower()
                            for val in obj_value.values()
                            if val
                            and isinstance(
                                val, str
                            )  # so we skip any falsy and non-str values
                        )
                        for target_item in filter_value
                    )
                else:
                    # Otherwise, just check for equality
                    return (
                        obj_value.lower() == filter_value.lower()
                        or filter_value.lower() in obj_value.lower()
                    )

            return list_condition

        def create_condition(key, value):
            # Handle list type preferences
            if isinstance(value, list):
                # If "any" is in the list, no filter is needed
                if "any" in [str(item).lower() for item in value]:
                    return None
                # Create a list condition for lists without "any"
                return create_list_condition(key, value)

            # Handle boolean type preferences
            elif isinstance(value, bool):
                if value is False:
                    return None
                if key in attribute_keys:
                    return (
                        lambda obj: obj.get("attributes", {}).get(key, False) == value
                    )
                elif key in environment_keys:
                    return (
                        lambda obj: obj.get("environment", {}).get(key, False) == value
                    )
                else:
                    return lambda obj: obj.get(key, False) == value

            # Handle string type preferences
            elif isinstance(value, str):
                value_lower = value.lower()
                if value_lower == "any":
                    return None
                if value_lower == "true":
                    if key in attribute_keys:
                        return (
                            lambda obj: obj.get("attributes", {}).get(key, False)
                            == True
                        )
                    elif key in environment_keys:
                        return (
                            lambda obj: obj.get("environment", {}).get(key, False)
                            == True
                        )
                    else:
                        return lambda obj: obj.get(key, False) == True
                elif value_lower == "false":
                    return None

            # Default to None if no condition is matched
            return None

        # Loop through the preferences and create lambda functions
        for key, value in preferences.items():
            condition = create_condition(key, value)

            # Avoid adding conditions for meta keys
            if condition and key not in ["species", "user_id"]:
                filter_conditions[key] = condition

        return filter_conditions

    def filter_results_list(self, filter_conditions, results_list):
        """function to filter lists of results

        Pass in lambda filter expressions as filters KWARG
        Pass in list to be filtered

        Lambda function filters by kwargs

        # Example usage
            animals = [
                {"name": "Biscuit", "coat": "Long", "colors":{
                "primary": "Tortoiseshell",
                "secondary": null,
                "tertiary": null
            }, "adoptable": True},
                {"name": "Phone", "coat": "Long", "colors":{
                "primary": "Tortoiseshell",
                "secondary": null,
                "tertiary": null
            }, "adoptable": False},
                {"name": "Tablet", "coat": "Long", "colors":{
                "primary": "Tortoiseshell",
                "secondary": null,
                "tertiary": null
            }, "adoptable": True},
                {"name": "Desktop", "coat": "Long", "colors":{
                "primary": "Tortoiseshell",
                "secondary": null,
                "tertiary": null
            }, "adoptable": True}
            ]
            #user preferences retrieved from db
            prefs = {
                "gender": ["any"],
                "shots_current": false,
                "spayed_neutered": false,
                "child_friendly": false,
                "dogs_friendly": false,
                "breeds": ["Afghan Hound", "Airedale Terrier", "Akbash", "Akita", "Alaskan Malamute", "American Bulldog", "American Bully", "American Eskimo Dog", "American Foxhound", "American Hairless Terrier", "American Staffordshire Terrier", "American Water Spaniel", "Anatolian Shepherd"],
                "coat": ["any"],
                "age": ["any"],
                "size": ["any"],
                "color": ["Apricot / Beige", "Bicolor", "Black", "Brindle", "Brown / Chocolate", "Golden", "Gray / Blue / Silver", "Harlequin", "Merle (Blue)", "Merle (Red)", "Red / Chestnut / Orange", "Sable", "Tricolor (Brown, Black, & White)"],
                "declawed": false,
                "special_needs": false,
                "house_trained": false,
                "cats_friendly": false,
                "personality_tags": ["any"],
                "gender": ["any"],
                            }

            filtered = self.filter_results_list(animals, prefs)
        """
        # initialize variables to be returned at end
        output = results_list
        bad_keys = []
        temp_output = []

        for key, condition in filter_conditions.items():
            for idx in range(len(results_list)):
                obj = results_list[idx]
                # check if current object meets the condition
                if condition(obj):
                    # parse obj for to use in templates easier
                    self.parse_api_animals_data(single_animal_data=obj)

                    # add obj to temp_output after parsing
                    temp_output.append(obj)
                    print("condition met for key=", key, len(temp_output))

            if not temp_output:
                bad_keys.append(key)
                flag = False
                print("condition NOT met for key=", key, len(temp_output))
                break

        # determine success (true/false) based on len(output) > 0
        flag = len(temp_output) > 0
        print(len(temp_output) > 0, len(temp_output))

        # return results_list if flag is false
        output = temp_output if flag else results_list
        # output = temp_output # if flag else results_list

        return {
            "results": output,
            "success_flag": flag,
            "bad_keys": bad_keys,
        }

    def get_mapped_animals_by_type(self, species, location_str, user_preferences_dict, page=1):
        """Function that takes two args: list_of_orgs and a user_id and sends a GET request to PetFinder API for animals that match preferences from the user_id argument

        Args:
            list_of_orgs (ARR or Pandas DataFrame): list of organization IDs from API in a Python List (Array) or a Pandas DataFrame format.
            user_id (INT): id of user making search request (eg. the user_id stored in 'g' -> g.user_id)
        """
        # dynamically handle gender
        gender_pref = user_preferences_dict.get("gender", ["any"])
        if len(gender_pref) == 0 or "any" in gender_pref or "unknown" in gender_pref:
            gender_pref = ["male", "female"]

        # dynamically handle coats
        default_coats = ("short", "medium", "long", "wire", "hairless", "curly")

        coats_pref = user_preferences_dict.get("coat", default_coats)
        coats_pref = (
            default_coats if len(coats_pref) == 0 or "any" in coats_pref else coats_pref
        )
        init_animals = self.petpy_api.animals(location=location_str, results_per_page=50, pages=page)
        # init_animals = self.petpy_api.animals(
        #     animal_type=species, location=location_str, sort="-recent"
        #     breed=user_preferences_dict.get("breed", []),
        #     gender=gender_pref,
        #     good_with_cats=user_preferences_dict.get("cats_friendly", False),
        #     good_with_children=user_preferences_dict.get("child_friendly", False),
        #     good_with_dogs=user_preferences_dict.get("dogs_friendly", False),
        #     declawed=user_preferences_dict.get("declawed", False),
        #     special_needs=user_preferences_dict.get("special_needs", False),
        #     house_trained=user_preferences_dict.get("house_trained", False),
        #     animal_type=species,
        #     coat=coats_pref,
        #     location=location_str,
        #     sort="distance",
        #     results_per_page=50,
        #     pages=page,
        # )["animals"]
        print("API results len = ", len(init_animals))
        # create filter conditions based on user_preferences_dict
        filter_conditions = self.create_filter_conditions(user_preferences_dict)

        # Now  use these filter conditions with filter_results_list function
        return self.filter_results_list(filter_conditions, init_animals)

    def animals_df_to_org_animal_count_dict(self, animals_df):
        """Function to group animals DataFrame by 'organization_id' and count the number of animals in each group, sorted by count in descending order, and return the result as a dictionary.

        Args:
            animals_df (DataFrame): pandas DataFrame of animals API results
        """

        # Group by 'organization_id' and count the number of animals in each group
        organization_counts = (
            animals_df.groupby("organization_id")
            .size()
            .reset_index(name="animal_count")
        )

        # Sort the groups by the count of animals in descending order
        organization_counts_sorted = organization_counts.sort_values(
            by="animal_count", ascending=False
        )

        # Convert the sorted DataFrame to a dictionary
        org_animal_count_dict = organization_counts_sorted.set_index("organization_id")[
            "animal_count"
        ].to_dict()

        return org_animal_count_dict

    def parse_breed(self, breeds_obj):
        """Function to parse breeds object property in a single Animal result from PetFinder API results"""
        if not breeds_obj or breeds_obj["unknown"] == True:
            return "Super Mutt"  # breed is Super Mutt by default

        primary = breeds_obj["primary"] or ""
        secondary = breeds_obj["secondary"] or False
        mixed_bool = breeds_obj["mixed"] or False
        unknown_bool = breeds_obj["unknown"] or False
        # check if unknown breed
        if unknown_bool == True:
            return "Super Mutt"
        # check if mixed breed
        if mixed_bool == True:
            # check if secondary breed is provided
            if secondary:
                return f"{primary} {secondary} mix"
            else:
                return f"{primary} Mix"
        else:
            return primary

    def parse_color(self, colors_obj):
        """Parse the colors object in an animal data object returned from API to remove false or null values"""
        print(colors_obj)
        if not colors_obj or not colors_obj["primary"]:
            return "Unknown Color"  # color is Unknown Color by default

        primary = colors_obj["primary"] or ""
        secondary = colors_obj["secondary"] or False
        tertiary = colors_obj["tertiary"] or False

        if tertiary:
            if secondary:
                print("parse colors output", f"{primary}/ {secondary}")
                return f"{primary}/ {secondary}"
            else:
                print("parse colors output", primary)
                return f"{primary}"
        else:
            print("parse colors output", primary)
            print("parse colors output")
            return primary

    def parse_photos(self, photos_list, type):
        """Function to parse breeds object property in API results"""

        # handle invalid or empty types
        if type.lower() not in [
            "dog",
            "cat",
            "horse",
            "bird",
            "rabbit",
            "small-furry",
            "barn-yard",
            "scales-fins-other",
        ]:
            type = "misc"

        # dictionary of urls for the graphics
        default_animal_graphic = {
            "dog": "../static/images/graphics/dog-freepik.png",
            "cat": "../static/images/graphics/cat-freepik.png",
            "horse": "../static/images/graphics/horse-freepik.png",
            "bird": "../static/images/graphics/bird-eucalyp.png",
            "small-furry": "../static/images/graphics/small-furry-freepik.png",
            "scales-fins-other": "../static/images/graphics/scales-smashicons.png",
            "barnyard": "../static/images/graphics/scales-smashicons.png",
            "rabbit": "../static/images/graphics/rabbit-freepik.png",
            "misc": "../static/images/graphics/tracks_freepik.png",
        }

        if not photos_list or len(photos_list) == 0:
            return default_animal_graphic[
                type.lower()
            ]  # return default graphic if the animal has no photos
        else:
            return photos_list[0]["full"]

    def parse_location_obj(self, loc_obj):
        """Function to parse location object property in API results"
        if not loc_obj or country:
                return None"""
        # grab city, state, country
        city = loc_obj.get("city", False)
        state = loc_obj.get("state", False)
        country = loc_obj.get("country", False)
        if country:
            # parse country string into 2 letter abbreviations
            country = (
                country
                if (len(country) == 2)
                else pycountry.countries.search_fuzzy(country)[0].alpha_2
            )
        if not loc_obj or not country:
            return None
        elif city:  # if city, state, country
            # clean city, state, country strings

            if state:
                # parse state string into 2 letter abbreviations
                state = (
                    state
                    if (len(state) == 2)
                    else pycountry.subdivisions.search_fuzzy(state)[0].alpha_2
                )
                return {
                    "location": "%s,%s" % (city, state),
                    "state": state,
                    "country": country,
                    "city": city,
                }
        else:  # if state, country
            if state:
                return {
                    "location": "%s,%s" % (state, country),
                    "state": state,
                    "country": country,
                }
            else:  # if only country
                return {
                    "location": "%s" % (country),
                    "country": country,
                }

    def parse_publish_date(self, pub_date, action="delta"):
        """Parse the published_date property in animal data object returned from API

        Args:
            pub_date (STRING): string date value returned from API
            action (STRING): the desired action to be done to the pub_date
                'delta' = get the difference between the pub_date and now() in days
                'format' = format the pub_date into a readable form
        """
        if action not in ["delta", "format"]:
            raise TypeError("Wrong Action Type")

        if not pub_date:
            raise TypeError("truthy pub_date value is not provided")

        # Using current time with UTC timezone
        today = datetime.datetime.now(pytz.utc)
        parsed_date = None

        # Determine the input date format
        if "/" in pub_date:
            input_format = "%d/%m/%Y"
        elif "T" in pub_date:
            input_format = "%Y-%m-%dT%H:%M:%S%z"
        else:
            raise ValueError(f"Unsupported date format: {pub_date}")

        # Parse the date
        date_obj = datetime.datetime.strptime(pub_date, input_format)

        # handle if action = 'delta'
        if action == "delta":
            # If the parsed date doesn't have timezone info, assume it's UTC
            if date_obj.tzinfo is None:
                date_obj = date_obj.replace(tzinfo=pytz.utc)
            date_diff = today - date_obj
            # get the difference in days
            parsed_date = date_diff.days
            return parsed_date

        # handle if action = 'format'
        if action == "format":
            parsed_date = date_obj.strftime("%d/%m/%Y")
            return parsed_date

    def parse_api_animals_data(self, single_animal_data):
        """
        Function to clean up missing data from api to be used in jinja templates

        Args:
            single_animal_data (dict): Python dictionary of a single animal data. This is API data to be cleaned up and turned into content for JINJA templates after filtering
        Use case:
            After filtering results_list in .get_mapped_animals_by_type(), pass each filtered `obj` into here
        """

        # Check if api_data is None or an empty string
        if single_animal_data is None or single_animal_data == "":
            print("Empty API data received.")
            return single_animal_data

        # copy the input obj
        parsed = single_animal_data.copy()
        try:
            # Parse the nested animal property objects

            # parse breeds
            single_animal_data["breeds"] = self.parse_breed(
                single_animal_data["breeds"]
            )
            # parse colors
            single_animal_data["colors"] = self.parse_color(
                colors_obj=single_animal_data["colors"]
            )
            # parse photos
            single_animal_data["photos"] = self.parse_photos(
                photos_list=single_animal_data.get("photos"),
                type=single_animal_data.get("type", "misc"),
            )
            # parse location
            single_animal_data["location"] = self.parse_location_obj(
                loc_obj=single_animal_data.get("contact")
            )
            # parse published_date
            single_animal_data["published_at"] = self.parse_publish_date(
                pub_date=single_animal_data.get("published_at", ""), action="format"
            )
            # create date_delta
            single_animal_data["date_delta"] = self.parse_publish_date(
                pub_date=single_animal_data.get("published_at", ""), action="delta"
            )

            # Remove videos
            if "videos" in single_animal_data:
                del single_animal_data["videos"]

        except TypeError as e:
            print(f"API data parsing error: {e}.")
            return single_animal_data

        # Return final list of parsed animals
        return parsed

    def find_highest_lowest(self, ani_objects, key="date_delta"):
        """
        Finds the animal objects with the highest and lowest values based on the specified key.
        Default key is 'date_delta" which would return the oldest and newest published animal
        Args:
            ani_objects (list): A list of objects (dictionaries).
            key (str): The key to use for comparison.

        Returns:
            tuple: A tuple containing the object with the highest value and the object with the lowest value.
        """
        if not ani_objects:
            return None, None

        highest_obj = ani_objects[0]
        lowest_obj = ani_objects[0]

        for obj in ani_objects:
            if obj[key] > highest_obj[key]:
                highest_obj = obj
            elif obj[key] < lowest_obj[key]:
                lowest_obj = obj

        return highest_obj, lowest_obj

    def get_top_results(self, parsed_data):
        """Function to sort parsed_data for top-results

        Args:
            parsed_data (LIST of OBJECTS): returned API results that have been parsed by self.parse_api_animals_data()

        Returns: OBJECT = {
            "oldest": value,
            "newest": value,
            "closest": value,
            "furthest": value
        }
        """
        oldest, newest = self.find_highest_lowest(
            ani_objects=parsed_data, key="date_delta"
        )
        furthest, closest = self.find_highest_lowest(
            ani_objects=parsed_data, key="distance"
        )

        # Pack into an object
        output_object = {
            "oldest": oldest,
            "newest": newest,
            "closest": closest,
            "furthest": furthest,
        }

        # filter out object keys with the falsy values
        output_object = {key: value for key, value in output_object if value}

        return output_object
