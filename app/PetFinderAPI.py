import os
from dotenv import load_dotenv
import datetime
from dateutil import parser
import pycountry
import pandas as pd
from flask import sessions, jsonify, json
from ratelimit import limits, RateLimitException
from backoff import expo, on_exception
from petpy import Petfinder

from models import User, UserAnimalPreferences  # , #UserPreferences

load_dotenv()


class PetFinderPetPyAPI:
    """
    API class with methods to store access PetFinder API and help functions to map user preference data to API search parameters
    """

    BASE_API_URL = os.environ.get("PETFINDER_API_URL", "https://api.petfinder.com/v2")
    if "https://" not in BASE_API_URL:
        BASE_API_URL = "https://" + BASE_API_URL

    # store default user_preference
    default_options_obj = {
        "location": "Toronto,ON",
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
        print(os.environ.get("API_KEY"), os.environ.get("API_SECRET"))
        self.petpy_api = Petfinder(
            key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET")
        )
        self.auth_token_time = datetime.datetime.now()
        # self.breed_choices = self.petpy_api.breeds() #commented out because

        # utilizing dependency injection here to prevent circular imports from app.py, form.py, helper.py and this file
        self.get_anon_preference = get_anon_preference_func
        self.get_user_preference = get_user_preference_func

    def create_custom_url_for_api_request(self, category, action, params):
        """Create a url to make an API request based off passed in params object.


        GET https://api.petfinder.com/v2/{CATEGORY}/{ACTION}?{parameter_1}={value_1}&{parameter_2}={value_2}

        Args:
            category (str): category of API to be called on eg. animal, animals, organization, organizations
            action(str): what REST request to make on API eg. 'get' = GET request
            params (OBJECT {str:str}): params Python OBJECT will be iterated on to create the key:value string queries to the url separated by question marks eg. `?{parameter_1}={value_1}`
        """

        # WRITE CODE HERE
        pass

    def get_orgs_id_list_from_df(self, params_obj):
        """Get DataFrame of animal rescue organizations within a specified distance of a location.

        Args:
            location (str, optional): Specified location. Defaults to 'Toronto, Ontario'.

        Returns:
            pandas.DataFrame: DataFrame of animal rescue organizations.
        """
        if not params_obj:
            params_obj = self.default_options_obj
        location = params_obj.get("location")
        try:
            init_orgs_df = self.petpy_api.organizations(location, sort="distance")
            filtered_list = init_orgs_df["id"].toList()
            print(filtered_list)
            return filtered_list
        except Exception as e:
            print(f"An error occurred while retrieving organizations: {e}")
            return None

    def get_animals_df(self, params_obj, user_bool, key="animal_types"):
        """Get DataFrame of animal rescue organizations within a specified distance of a location.

        Args:
            params_obj (DICT) dictionary of search parameters
            user_bool (BOOL) is user logged in (True) or not (False)
        Returns:
            pandas.DataFrame: DataFrame of animal rescue organizations.
        """

        if not params_obj:
            saved_pref = (
                {**self.get_user_preference_func(key=key)}
                if user_bool
                else {**self.get_anon_preference_func(key=key)}
            )
            params_obj = {key: saved_pref.get(key).data}
        try:

            # Fetch data from API
            animals_df = self.petpy_api.animals(**params_obj)
            animal_types = params_obj.get(
                key,
                (
                    self.get_user_preference_func(key=key)
                    if user_bool
                    else self.get_anon_preference_func(key=key)
                ),
            )
            # Filter DataFrame based on 'animal_types'
            if animal_types:
                animals_df = animals_df[animals_df["type"].isin(animal_types)]

            return animals_df

        except Exception as e:
            print(f"An error occurred while retrieving organizations: {e}")
            return None

    def map_user_form_data(self, form_data):
        """
        Function to map user preferences to a dictionary object.

        Args:
            form_data (DICTIONARY): DICTIONARY object of user preferences form data.

        Returns:
            dict: Dictionary containing mapped user preferences.
        """
        mapped_data_obj = {**{key: value for key, value in form_data.items() if value}}
        mapped_data_obj.update(self.default_options_obj)
        return mapped_data_obj

    def get_animals_as_per_user_preferences(self, session, animal_types, country):
        """Function that takes two args: list_of_orgs and a user_id and sends a GET request to PetFinder API for animals that match preferences from the user_id argument

        Args:
            list_of_orgs (ARR or Pandas DataFrame): list of organization IDs from API in a Python List (Array) or a Pandas DataFrame format.
            user_id (INT): id of user making search request (eg. the user_id stored in 'g' -> g.user_id)
        """

        user_id = session["CURR_USER_KEY"] if "CURR_USER_KEY" in session else None

        # handle logged in user
        if user_id:
            user_preferences = UserAnimalPreferences.query.get_or_404(
                User.id == user_id
            ).all()
            if user_preferences:
                # filter results by animal_type
                filtered_user_preferences = list(
                    filter(
                        lambda search_val: search_val == animal_types, user_preferences
                    )
                )

                # grab data in the following user preferences columns: ['user_preference_name', 'user_preference_data']
                pref_key_list = {
                    key: value
                    for key, value in filtered_user_preferences
                    if key in ["user_preference_name", "user_preference_data"]
                }

                # add default search parameters
                default = self.default_options_obj
                pref_key_list = default.update(pref_key_list)
                matching_animals = self.petpy_api.animals(pref_key_list)

            # handle no saved user preferences found by passing in default search parameters
            else:
                pref_key_list = self.default_options_obj
                matching_animals = self.petpy_api.animals(pref_key_list)

        # handle anon users
        else:
            # populate pref_key_obj with anon preferences
            pref_key_obj = {"location": country, "animal_types": animal_types}
            print(pref_key_obj)
            matching_animals = self.petpy_api.animals(**pref_key_obj)

            return matching_animals

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

        if not colors_obj or colors_obj["primary"] == False:
            return "Unknown Color"  # color is Unknown Color by default

        primary = colors_obj["primary"] or ""
        secondary = colors_obj["secondary"] or False
        tertiary = colors_obj["tertiary"] or False

        if tertiary:
            if secondary:
                return f"{primary}, {secondary}"
            else:
                return f"{primary}"
        else:
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
        print(f"parse_location obj func call: loc_obj: {loc_obj}")
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
            print(country)
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
                print(state)
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
            raise TypeError('truthy pub_date value is not provided')

        # Using current time with UTC timezone
        today = datetime.datetime.now(datetime.timezone.utc)
        parsed_date = None

        # handle if action = 'delta'
        if action == "delta":
            date_obj = datetime.datetime.fromisoformat(pub_date.replace("+0000", "+00:00"))
            date_diff = today - date_obj
            # get the difference in days
            parsed_date = date_diff.days
            return parsed_date

        # handle if action = 'format'
        if action == "format":
            date_obj = datetime.datetime.fromisoformat(pub_date.replace("Z", "+00:00").replace("+0000", "+00:00"))
            parsed_date = date_obj.strftime("%d/%m/%Y")
            return parsed_date

    def parse_api_animals_data(self, api_data):
        """
        Function to clean up missing data from api to be used in jinja templates

        Args:
            api_data (json): API data to be cleaned up and turned into content for JINJA templates
        """
        # output list of parsed animals
        parsed = []

        # Check if api_data is None or an empty string
        if api_data is None or api_data == "":
            print("Empty API data received.")
            return parsed

        # Assume api_data is a string (JSON string)
        try:
            data = json.loads(api_data)
        except TypeError as e:
            print(f"Error parsing JSON data: {e}")
            # If parsing fails, assume api_data is already in the desired format
            data = api_data["animals"]
            print(f"Animals received from API: {len(api_data['animals'])}")

        # Check if data is a list of dictionaries
        if isinstance(data, list) and all(isinstance(item, dict) for item in data):
            for animal in data:
                # Parse the nested animal property objects
                animal["breeds"] = self.parse_breed(animal["breeds"])
                animal["color"] = self.parse_color(colors_obj=animal["colors"])
                animal["photos"] = self.parse_photos(
                    photos_list=animal.get("photos"), type=animal.get("type", "misc")
                )
                animal["location"] = self.parse_location_obj(
                    loc_obj=animal.get("contact")
                )
                animal["published_date"] = self.parse_publish_date(
                    pub_date=animal.get("published_date", ""), action="format"
                )
                animal["date_delta"] = self.parse_publish_date(
                    pub_date=animal.get("published_date", ""), action="delta"
                )

                # Remove videos
                if "videos" in animal:
                    del animal["videos"]
                parsed.append(animal)
        else:
            print(
                "Data is not valid python lists; data not in the expected format."
            )  # data is not a list of dictionaries
            print(f"Animal #{len(parsed) + 1}: {parsed}")

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
