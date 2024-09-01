import os
from dotenv import load_dotenv
import datetime
import pytz
from dateutil import parser
import pycountry
import pandas as pd
from flask import sessions, jsonify, json
from ratelimit import limits, RateLimitException
from petpy import Petfinder

from ..models import User, UserAnimalPreferences  # , #UserPreferences

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
            """helper function that uses a closure to prevent scope pollution but still has access to key, value from outer parent function
            
            
            use case: intended to handle creating conditions for lists containing varying data structures
            returns condition
            """
            def list_condition(obj):
                obj_value = obj.get(filter_key, [])
                if isinstance(obj_value, dict):
                    return all(any(item == v for v in obj_value.values()) for item in filter_value)
                elif isinstance(obj_value, list):
                    return all(item in obj_value for item in filter_value)
                else:
                    return obj_value == filter_value
            return list_condition
        
        def create_condition(key, value):
            #handle if the preference value is a list
            if isinstance(value, list):
                #handle if any is contained in `value` => return no condition as no filtering is needed
                if "any" in [str(item).lower() for item in value]:
                    return None 
                #call helper function to handle if`value` has `list` type but does not contain `any`  
                return create_list_condition(key, value)    
            
            #handle if the preference value is a boolean
            elif isinstance(value, bool):
                if not value or "False":
                    return None
                if key in attribute_keys:
                    return lambda obj: obj.get('attributes', {}).get(key, False) == value
                elif key in environment_keys:
                    return lambda obj: obj.get('environment', {}).get(key, False) == value
                else:
                    return lambda obj: obj.get(key, False) == value
            elif isinstance(value, str):
                if value.lower() == "any":
                    return None
                if value.lower() == "true":
                    if key in attribute_keys:
                        return lambda obj: obj.get('attributes', {}).get(key, False) == True
                    elif key in environment_keys:
                        return lambda obj: obj.get('environment', {}).get(key, False) == True
                    else:
                        return lambda obj: obj.get(key, False) == True
                if value.lower() == "false":
                    return None
            return None
        
        #loop through the preferences object and create lambda functions from the key:value pairings
        for key, value in preferences.items():
            if key not in ["species", "user_id"]: #avoid passing in meta info
                condition = create_condition(key, value)
                if condition:
                    filter_conditions[key] = condition

        return filter_conditions
    
    def filter_results_list(self, filter_conditions, results_list):
        """function to filter lists of results

        Pass in lambda filter expressions as filters KWARG
        Pass in list to be filtered

        Lambda function filters by kwargs

        # Example usage
            animals = [
                {"name": "Laptop", "coat": ["Long"], "adoptable": True},
                {"name": "Phone", "coat": ["Long"], "adoptable": False},
                {"name": "Tablet", "coat": ["Long"], "adoptable": True},
                {"name": "Desktop", "coat": ["Long"], "adoptable": True}
            ]

            filtered_animals = filter_objects(
                {
                    "coat_check": lambda animal: animal["coat"] < 800,
                    "adoptable": lambda animal: animal["adoptable"]
                },
                animals
            )
        """
        #initialize variables to be returned at end
        output = results_list
        bad_keys = []

        for key, condition in filter_conditions.items():
            temp_output = []
            for obj in output:
                #check if current object meets the condition
                if condition(obj):
                    temp_output.append(obj)
            
            if not temp_output:
                bad_keys.append(key)
                flag = False
                break
            
        #determine success (true/false) based on len(output) > 0 
        flag = len(output) > 0
        #return results_list if flag is false
        # output = temp_output if flag else results_list
        output = temp_output # if flag else results_list

        return {
            "results": output,
            "success_flag": flag,
            "bad_keys": bad_keys,
        }
        
    def get_mapped_animals_by_type(self, species, location_str, user_preferences_dict):
        """Function that takes two args: list_of_orgs and a user_id and sends a GET request to PetFinder API for animals that match preferences from the user_id argument

        Args:
            list_of_orgs (ARR or Pandas DataFrame): list of organization IDs from API in a Python List (Array) or a Pandas DataFrame format.
            user_id (INT): id of user making search request (eg. the user_id stored in 'g' -> g.user_id)
        """
        init_animals = self.petpy_api.animals(
                animal_type=species, location=location_str, sort="-recent"
            )["animals"]
        #create filter conditions based on user_preferences_dict
        filter_conditions = self.create_filter_conditions(user_preferences_dict)

        # Now you can use these filter conditions with your filter_results_list function
        return self.filter_results_list(filter_conditions, init_animals)
        
        # if not user_preferences_dict:
        #     user_preferences_dict = {}
        #     init_animals = self.petpy_api.animals(
        #         animal_type=species, location=location_str, sort="-recent"
        #     )
        #     return init_animals
        # else:
        #     # declare flag & bad_keys
        #     # flag = boolean indicator if length of results list is > 0
        #     flag = True

        #     # bad_keys = list of preference keys that cause the length of results list to go to 0 when filtered
        #     bad_keys = []

        #     if "personality" in user_preferences_dict:
        #         personality = user_preferences_dict["personality"]
        #         del user_preferences_dict["personality"]

        #     # get init_animals
        #     init_animals = self.petpy_api.animals(
        #         animal_type=species,
        #         location=location_str,
        #         sort="-recent",
        #         **user_preferences_dict,
        #     )

        #     # first filter by personality
        #     filtered_by_personality = self.filter_results_list(
        #         {"personality": lambda result: result["tags"] in personality},
        #         init_animals,
        #     )
        #     # handle if personality filter is too restrictive and results in len of 0 results
        #     filtered_results_list = (
        #         filtered_by_personality
        #         if len(filtered_by_personality) > 0
        #         else init_animals
        #     )

        #     # Loop through the rest of preferences
        #     for pref_key in user_preferences_dict:
        #         # Handle if list value
        #         pref_list_value = user_preferences_dict[pref_key]
        #         # if "any" is the pref list value, do not filter and move on
        #         if (
        #             pref_list_value.lower() == "any"
        #             or pref_list_value[0].lower() == "any"
        #         ):
        #             next()

        #         if isinstance(pref_list_value, list):
        #             # Lambda expression to check if main_list contains all elements of sub_list
        #             expression = lambda results_list: all(
        #                 item in results_list for item in pref_list_value
        #             )

        #             # Assuming init_animals is a list that needs to be filtered
        #             filtered_results_list = self.filter_results_list(
        #                 expression, filtered_results_list
        #             )
        #         # handle if boolean value
        #         elif isinstance(pref_list_value, str, bool):
        #             if pref_list_value == "True" or pref_list_value == True:
        #                 # filter by results
        #                 # create boolean filter express

        #                 if pref_key in [
        #                     "spayed_neutered",
        #                     "house_trained",
        #                     "declawed",
        #                     "special_needs",
        #                     "shots_current",
        #                 ]:
        #                     key = "attributes"
        #                 elif pref_key in [
        #                     "child_friendly",
        #                     "dogs_friendly",
        #                     "cats_friendly",
        #                 ]:
        #                     key = "environment"

        #                 expression = (
        #                     lambda results_list: results_list[key][pref_key]
        #                     == pref_list_value
        #                 )
        #                 filtered_results_list = self.filter_results_list(
        #                     expression, filtered_results_list
        #                 )

        #     return {
        #         "success_flag": flag,
        #         "bad_keys": bad_keys,
        #         "results": filtered_results_list,
        #     }

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

        # handle if action = 'delta'
        if action == "delta":
            date_obj = datetime.datetime.strptime(pub_date, "%Y-%m-%dT%H:%M:%S%z")
            date_diff = today - date_obj
            # get the difference in days
            parsed_date = date_diff.days
            return parsed_date

        # handle if action = 'format'
        if action == "format":
            date_obj = datetime.datetime.strptime(pub_date, "%Y-%m-%dT%H:%M:%S%z")
            parsed_date = datetime.datetime.strftime(date_obj, "%d/%m/%Y")
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
