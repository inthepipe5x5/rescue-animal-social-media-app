import os
from dotenv import load_dotenv
from dateutil import parser
import time
import pandas as pd
from flask import json
from ratelimit import limits, RateLimitException
from petpy import Petfinder
import requests
from package.parse import parse_multi_animal

# from ..models import User, UserAnimalPreferences  # , #UserPreferences

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
        "location": "Toronto, ON",
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
    # user prefs that map to search params
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
    # keys that are dynamically generated
    dynamic_keys = [
        "breed",
        "coat",
        "colors",
        "gender",
        "size",
        "personality",
        "age",
    ]
    _petpy_api_instance = None

    def __init__(self):
        self.access_token = None
        self.token_expiration = None

    @classmethod
    def petpy_api(cls):
        if cls._petpy_api_instance is None:
            cls._petpy_api_instance = Petfinder(
                key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET")
            )
        return cls._petpy_api_instance

    def _get_access_token(self):
        """Instance method to request a new access token from Petfinder API

        Raises:
            Exception: "Error getting access token @ URL {url}: {response.status_code} - {response.text}"

        Returns:
            access_token: PetFinder API access token
        """
        current_time = int(time.time())

        # Check if instance has a valid token
        if self.access_token and current_time < self.token_expiration:
            return self.access_token

        # If not, request a new token
        payload = {
            "grant_type": "client_credentials",
            "client_id": os.environ.get("API_KEY"),
            "client_secret": os.environ.get("API_SECRET"),
        }
        url = self.BASE_API_URL + "/oauth2/token"
        response = requests.post(url, data=payload)

        if response.status_code == 200:
            token_info = response.json()
            self.access_token = token_info["access_token"]
            self.token_expiration = current_time + token_info["expires_in"]
            return self.access_token
        else:
            raise Exception(
                f"Error getting access token @ URL {url}: {response.status_code} - {response.text}"
            )

    def _get_request(
        self,
        endpoint="animals",
        request_url="https://api.petfinder.com/v2/animals",
        **params,
    ):
        """Create a url to make an API request based off passed in params object.


        GET https://api.petfinder.com/v2/{CATEGORY}/?{parameter_1}={value_1}&{parameter_2}={value_2}

        Args:
            category (str): category of API to be called on eg. animal, animals, organization, organizations
            action(str): what REST request to make on API eg. 'get' = GET request
            params (OBJECT {str:str}): params Python OBJECT will be iterated on to create the key:value string queries to the url separated by question marks eg. `?{parameter_1}={value_1}`
        """
        # handle if no params passed in
        params = {} if not params else params

        # Obtain the current access token within the self._get_access_token() instead of helper petpy_api class
        access_token = self._get_access_token()
        print("_get_request", access_token)

        # Make a request to the specified endpoint with the access token
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = requests.get(request_url, headers=headers, params=params)
            # Check for a successful response
            response.raise_for_status()
            result = response.json()

            output = {
                "access_token": access_token,
                "results": result[endpoint],
                "pagination": result["pagination"],
                "success_flag": (len(result[endpoint]) > 0),
                "status_code": response.status_code or 200,
            }
            # print(output)
            return output
        except Exception as e:
            print(f"endpoint, request_url, params=> { request_url, params}")
            print(f"_get_request ERROR=> ERROR: {e}")
            return {
                "access_token": access_token,
                "results": response,
                "pagination": [],
                "success_flag": False,
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
        if not bool(preferences):
            return filter_conditions

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
                    # Otherwise, check for equality or inclusion based on the type of filter_value
                    if isinstance(filter_value, (str, bool)):
                        return str(obj_value).lower() == str(filter_value).lower()
                    elif isinstance(filter_value, dict):
                        return obj_value in filter_value.keys()
                    elif isinstance(filter_value, list):
                        return str(obj_value).lower() in [
                            str(val).lower() for val in filter_value
                        ]
                    else:
                        return None  # Handle any other unexpected types

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
                if key in self.attribute_keys:
                    return (
                        lambda obj: obj.get("attributes", {}).get(key, False) == value
                    )
                elif key in self.environment_keys:
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
                    if key in self.attribute_keys:
                        return (
                            lambda obj: obj.get("attributes", {}).get(key, False)
                            == True
                        )
                    elif key in self.environment_keys:
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

    def preprocess_preferences(self, init_params_copy, prefs_obj):
        """helper function to preprocess user prefs_obj and reduce if they include any values in excluded_values (ie. "any"/False)
        use this to create search params mapped to PetPy animals function parameter requirements

        Args:
            init_params_copy (_type_): copy of init search params
            prefs_obj (dict): user preferences

        Returns:
            dict: search parameters
        """
        # if prefs_obj is falsy, return empty object
        if not prefs_obj:
            return {}

        # prefs that only have true/false/None possibilities
        boolean_prefs = {
            bool_key: False for bool_key in self.environment_keys + self.attribute_keys
        }

        # prefs that only have 'any' or a list possibilities
        any_prefs = {pref_key: ["any"] for pref_key in self.dynamic_keys}

        # Update prefs_obj with boolean and any prefs
        prefs_obj.update(boolean_prefs)
        prefs_obj.update(any_prefs)

        excluded_values = ["any", "Any", "ANY", "/Any/", "/any/", "false", False, None]

        # dynamically handle gender
        gender_pref = prefs_obj.get("gender", ["any"])
        if len(gender_pref) == 0 or "any" in gender_pref or "unknown" in gender_pref:
            gender_pref = ["male", "female"]

        # dynamically handle coats
        default_coats = ("short", "medium", "long", "wire", "hairless", "curly")
        coats_pref = prefs_obj.get("coat", default_coats)
        coats_pref = (
            default_coats if len(coats_pref) == 0 or "any" in coats_pref else coats_pref
        )

        # Initialize search params
        mapped_search_params = init_params_copy.copy()

        # Filter prefs_obj
        for key, value in prefs_obj.items():
            if isinstance(value, (str, bool)):
                if value not in excluded_values:
                    mapped_search_params[key] = value
            elif isinstance(value, list):
                filtered_list = [item for item in value if item not in excluded_values]
                if filtered_list:
                    mapped_search_params[key] = filtered_list
            elif isinstance(value, dict):
                filtered_dict = {
                    k: v for k, v in value.items() if v not in excluded_values
                }
                if filtered_dict:
                    mapped_search_params[key] = filtered_dict

        search_params = (
            mapped_search_params if mapped_search_params else init_params_copy
        )
        print(search_params, "being passed as params to /animals API call")
        return search_params

    def filter_results_list(
        self,
        filter_conditions,
        results_list,
    ):
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
        # handle if filter_conditions is falsy
        if not bool(results_list):
            # immediately return results_list
            return {
                "results": [],
                "success_flag": False,  # False since no result output
                "unfiltered": True,  # True since no filtering was done
                "bad_keys": bad_keys,
            }
        # initialize variables to be returned at end
        output = results_list
        bad_keys = []
        temp_output = []
        # handle if filter_conditions is falsy but results_list is truthy
        if not bool(filter_conditions) and bool(results_list):
            # immediately return results_list
            return {
                "results": output,
                "success_flag": True,  # True since technically there are no filters to "fail"
                "unfiltered": True,  # True since no filtering was done
                "bad_keys": bad_keys,
            }

        for key, condition in filter_conditions.items():
            for idx in range(len(output)):
                obj = output[idx]
                # check if current object meets the condition
                if condition(obj):
                    # parse obj for to use in templates easier

                    # add obj to temp_output after parsing
                    temp_output.append(obj)
                    print("condition met for key=", key, len(temp_output))

            if not temp_output:
                bad_keys.append(key)
                flag = False
                print("condition NOT met for key=", key, len(temp_output))
                break  # stop loop #DO LATER; perhaps make the for loop a recursive helper function call that removes the "bad_key" from filter conditions and reruns filtering until len(temp_output) > 0

        # determine success (true/false) based on len(output) > 0
        flag = len(temp_output) > 0
        print(len(temp_output) > 0, len(temp_output))

        # return results_list if flag is false
        output = temp_output if flag else results_list
        # output = temp_output # if flag else results_list
        # determine if unfiltered_results are passed back
        unfiltered = True if len(temp_output) > 0 and output == results_list else False
        return {
            "results": output,
            "success_flag": flag,
            "unfiltered": unfiltered,
            "bad_keys": bad_keys,
        }

    def get_mapped_animals_by_type(
        self, species, location_str, distance=100, user_preferences_dict={}, page=1
    ):
        init_params = {
            "type": species,
            "page": page,
            "location": location_str,
            "distance": distance,
        }
        params = self.preprocess_preferences(
            init_params_copy=init_params.copy(), prefs_obj=user_preferences_dict
        )
        print("api params =>", params)
        # grab initial animal results with pre-processed mapped search params
        init_animals = self._get_request(
            request_url="https://api.petfinder.com/v2/animals", params=params
        )
        # REMOVE LATER
        print("API results len = ", len(init_animals["results"]))

        # if initial results are empty, try again with default search params
        if len(init_animals["results"]) == 0:
            init_animals = self._get_request(
                request_url="https://api.petfinder.com/v2/animals", params=init_params
            )

            # REMOVE LATER
            print(
                "Refetched API results len = ",
                len(init_animals["results"]),
            )

        # create filter conditions based on user preferences
        filter_conditions = self.create_filter_conditions(user_preferences_dict)

        # filter the results using the conditions
        filtered = self.filter_results_list(
            filter_conditions=filter_conditions,
            results_list=init_animals["results"],
        )

        # check filtering success
        name_of_filtered = (
            [animal["name"] for animal in filtered["results"]]
            if len(filtered["results"]) > 0
            else []
        )
        print("Filtering success:", filtered["success_flag"], name_of_filtered)

        # parse the filtered results
        if filtered["success_flag"] and len(filtered["results"]) > 0:
            parsed_and_filtered = parse_multi_animal(animal_list=filtered["results"])
        else:
            parsed_and_filtered = []

        return {
            "pagination": init_animals["pagination"],
            "results": parsed_and_filtered,
            "success_flag": filtered["success_flag"] and len(parsed_and_filtered),
        }

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
            parsed_data (LIST of OBJECTS): returned API results that have been parsed by parsed_result = ParseAnimal()

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
