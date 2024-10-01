import os
from dotenv import load_dotenv
from dateutil import parser
import time
import pandas as pd
from flask import json
from ratelimit import limits, RateLimitException
from petpy import Petfinder
import requests
from json import JSONDecodeError
from package.parse import parse_multi_animal

# from ..models import User, UserAnimalPreferences  # , #UserPreferences

load_dotenv()
from ratelimit import limits, sleep_and_retry


class PetFinderPetPyAPI:
    """
    API class with methods to store access PetFinder API and help functions to map user preference data to API search parameters
    """

    BASE_API_URL = os.environ.get("PETFINDER_API_URL", "https://api.petfinder.com/v2")
    if "https://" not in BASE_API_URL:
        BASE_API_URL = "https://" + BASE_API_URL

    # Define limit for generator function to make API calls as PetFinder limits to 1000 calls per day
    API_CALLS_PER_DAY = 1000
    TIME_PERIOD = 86400  # Time period in seconds (86400 seconds = 24 hours)

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
        "color",
        "gender",
        "size",
        "personality",
        "age",
    ]
    _petpy_api_instance = None

    def __init__(self, *args, **kwargs):
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

        # Retry mechanism
        for _ in range(3):  # Retry up to 3 times
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                token_info = response.json()
                self.access_token = token_info["access_token"]
                self.token_expiration = current_time + token_info["expires_in"]
                print("new access_token received PetFinderAPI and api instance updated")
                return self.access_token
            elif response.status_code == 500:
                time.sleep(2)  # Sleep for 2 seconds before retrying
            else:
                raise Exception(
                    f"Error getting access token @ URL {url}: {response.status_code} - {response.text}"
                )
        raise Exception(f"Failed to get access token after multiple attempts.")

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

        if params:
            # Handle multiple values for the same parameter
            formatted_params = {}
            for key, value in params.items():
                if isinstance(value, list):
                    formatted_params[key] = ",".join(map(str, value))
                else:
                    formatted_params[key] = value
            # set params to formatted_params after joining strings
            params = formatted_params

        # Make a request to the specified endpoint with the access token
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = requests.get(request_url, headers=headers, params=params)
            print(f"_GET_REQUEST() Response: {response.status_code}")

            # Check for a successful response
            response.raise_for_status()
            result = response.json()
            status_code = response.status_code
            
            result["status_code"] = status_code
            result['results']  = result.get(endpoint, [])
            del result[endpoint]
            return result
            # output = {
            #     "access_token": access_token,
            #     "results": result.get(endpoint, []),
            #     "pagination": result.get("pagination", {}),
            #     "success_flag": bool(result.get(endpoint)),
            #     "status_code": response.status_code,
            # }
            # print("get request status", output["status_code"])
            # return output

        except Exception as e:
            print(f"endpoint, request_url, params=> { request_url, params}")
            print(f"_get_request ERROR=> ERROR: {e}")

            # If the response is unavailable or invalid, the nested try/exception falls back on empty values for results and pagination.
            try:
                # Try extracting JSON from response if possible
                response = response if "response" in locals() else {}
            except Exception:
                # Use locals() handle the absence of result or response
                # FYI Lin => locals() is a built-in Python function that returns a dictionary of the local variables in the current scope, allowing you to check if a variable exists before using it.
                return {
                    "message": str(e),
                    "results": (
                        result.get("results", []) if "result" in locals() else []
                    ),
                    "pagination": (
                        result.get("pagination", {}) if "result" in locals() else {}
                    ),
                    "status_code": (
                        response.status_code if "response" in locals() else 500
                    ),
                    "success_flag": False,
                }

        except JSONDecodeError as e:
            print("response was not in JSON")
            if "response" in locals():
                return response
            else:
                return {"message": e, "status_code": 500}

        except requests.exceptions.RequestException as e:
            print(f"endpoint, request_url, params=> {request_url, params}")
            print(f"_get_request ERROR=> ERROR: {e}")

            error_response = {}
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_response = e.response.json()
                except ValueError:
                    error_response = {"text": e.response.text}

            return {
                "message": str(e),
                "results": error_response.get(endpoint, []),
                "pagination": error_response.get("pagination", {}),
                "status_code": (
                    e.response.status_code if hasattr(e, "response") else 500
                ),
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
        if not preferences:
            return filter_conditions

        def create_list_condition(filter_key, filter_value, nested_key=None):
            """
            Create a condition function for a list type preference, including handling of nested properties.

            Args:
            filter_key (str): The key in the object to filter.
            filter_value (list): The list of acceptable values.
            nested_key (str, optional): If filtering based on a nested object, the key for that nested object.

            Returns:
            function: A lambda function representing the filter condition.
            """

            def list_condition(obj_to_filter):
                # obj_value => value to match when filtering
                # Handle nested fields
                if nested_key:
                    obj_value = obj_to_filter.get(nested_key, {}).get(filter_key, [])
                else:
                    obj_value = obj_to_filter.get(filter_key, [])

                if isinstance(obj_value, list):
                    # handle if obj_value is empty list
                    if obj_value and len(obj_value) > 0:
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
            # Special handling for address filtering
            if key in ["country", "state"]:
                # Handle string type filtering for country/state
                if isinstance(value, str):
                    # Create a lambda function to directly compare string values in contact.address
                    """
                    example of this:
                    lambda obj: obj.get("contact", {}).get("address", {}).get("country", "").lower() == "ca"
                    lambda obj: obj.get("contact", {}).get("address", {}).get("state", "").lower() == "on"
                    """
                    return (
                        lambda obj: obj.get("contact", {})
                        .get("address", {})
                        .get(key, "")
                        .lower()
                        == value.lower()
                    )
                elif isinstance(value, list) and "any" in [
                    str(item).lower() for item in value
                ]:
                    return None
                # Otherwise, create a list condition for lists without "any"
                return create_list_condition(key, value, nested_key="contact.address")

            # Handle other list type preferences
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
                if value_lower in ["any", "false", False]:
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
                        # Correct string comparison for equality
                        return lambda obj: obj.get(key, "").lower() == value_lower

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
            return init_params_copy if init_params_copy else {}
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

        # dynamically handle "coats" as the PetFinder API accepts "coat" as a query param in GET request but returns key as "coats" in response
        if "coats" in prefs_obj:
            # set value to value of "coats" and delete "coats" key:value
            prefs_obj["coat"] = prefs_obj["coats"]
            del prefs_obj["coats"]

        # dynamically handle coats
        default_coats = ("short", "medium", "long", "wire", "hairless", "curly")
        coats_pref = prefs_obj.get("coat", default_coats)
        coats_pref = (
            default_coats if len(coats_pref) == 0 or "any" in coats_pref else coats_pref
        )

        # dynamically handle "colors" as the PetFinder API accepts "color" as a query param in GET request but returns key as "colors" in response
        if "colors" in prefs_obj:
            # set value to value of "colors" and delete "colors" key:value
            prefs_obj["color"] = prefs_obj["colors"]
            del prefs_obj["colors"]

        # Initialize search params
        mapped_search_params = init_params_copy.copy()

        # Filter prefs_obj to remove any 'keys' that include an excluded value
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
                # add filtered_dict if the key is not
                if filtered_dict and key not in [
                    "dog",
                    "cat",
                    "rabbit",
                    "small-furry",
                    "horse",
                    "bird",
                    "scales-fins-other",
                    "barnyard",
                ]:
                    mapped_search_params[key] = filtered_dict

        # Check for empty search params, and return original if none were added
        search_params = (
            mapped_search_params if mapped_search_params else init_params_copy
        )

        # Ensure proper query string encoding (flatten any complex structures)
        flattened_params = {
            key: ",".join(value) if isinstance(value, list) else value
            for key, value in search_params.items()
        }

        # # TODO: REMOVE LATER
        # # Debugging for visualization of params
        print(flattened_params, "being passed as params to /animals API call")

        return flattened_params

    def filter_results_list(self, filter_conditions, results_list):
        """Filters a list of results based on provided lambda conditions.

        Parameters:
            filter_conditions (dict): Dictionary where keys are filter names and values are lambda functions that return True/False.
            results_list (list): List of objects to filter.

        Returns:
            dict: Contains filtered results, success flag, unfiltered flag, and bad keys (failed conditions).
        """

        # Handle empty result list
        if not results_list:
            return {
                "results": [],
                "success_flag": False,
                "unfiltered": True,
                "bad_keys": [],
            }

        # Handle no filter conditions
        if not filter_conditions:
            return {
                "results": results_list,
                "success_flag": True,
                "unfiltered": True,
                "bad_keys": [],
            }

        # Initialize the output list and track bad keys
        temp_output = results_list  # Start with full list
        bad_keys = []

        # Loop through each filter condition
        for key, condition in filter_conditions.items():
            filtered_output = []  # Temporary filtered list for this condition
            for obj in temp_output:
                # Apply filter condition to each object
                if condition(obj):
                    filtered_output.append(obj)

            # If no objects matched this condition, mark the key as bad
            if not filtered_output:
                bad_keys.append(key)
            else:
                # Continue filtering the reduced list
                temp_output = filtered_output

        # Check if any objects passed all conditions
        success_flag = bool(temp_output)

        # Determine if the original list was returned
        unfiltered = len(temp_output) == len(results_list)

        # Final output
        return {
            "results": temp_output if success_flag else results_list,
            "success_flag": success_flag,
            "unfiltered": unfiltered,
            "bad_keys": bad_keys,
        }

    def split_animals_by_type(self, animals):
        """
        The function `split_animals_by_type` categorizes a list of animals based on their type.

        :param animals: The `split_animals_by_type` function takes a list of dictionaries representing
        animals as input. Each dictionary should have a key 'type' that specifies the type of animal. If the
        'type' key is missing in a dictionary, it defaults to 'Unknown'
        :return: The function `split_animals_by_type` returns a dictionary where the keys are the types of
        animals found in the input list `animals`, and the values are lists of animals of that type.

        Example use:
        animal_list = PetFinderPetPyAPI._get_request(url="/animals")

        split_list_by_animal_type = split_animals_by_type(animals=animal_list)

        """
        animal_groups = {}
        if not animals:
            return animal_groups

        for animal in animals:
            animal_type = animal.get("type", "Unknown")
            if animal_type not in animal_groups:
                animal_groups[str(animal_type.lower())] = []
            animal_groups[str(animal_type.lower())].append(animal)

        return animal_groups

    @sleep_and_retry
    @limits(calls=API_CALLS_PER_DAY, period=TIME_PERIOD)
    def animal_pagination_generator(
        self, init_params, target_page, favorites=[], user_preferences_dict={}
    ):
        """Generator for paginating through animal results."""

        # Preprocess animal preferences => reduce to "real" preferences that are not "any"/False
        params = self.preprocess_preferences(
            init_params_copy=init_params.copy(), prefs_obj=user_preferences_dict
        )

        page = init_params.get("page", 1)
        bad_keys = set()

        while True:
            # Fetch results
            print(
                f"Making API call with params: {params}"
            )  # REMOVE LATER AFTER DEBUGGING IS DONE
            response = self._get_request(
                request_url="https://api.petfinder.com/v2/animals", params=params
            )

            if response is None:  # Handle None response from API
                print("Received None response from API.")
                break

            # Check if response is None or not a dict
            if not isinstance(response, dict):
                print(
                    f"Invalid response received in ANIMAL_PAGINATION_GENERATOR(): {response}"
                )  # for debugging purposes
                break  # exit the while loop if response is invalid

            # Check for response code or errors in the API response
            if str(response.get("status_code", ""))[0] != "2":
                print(
                    f"Non-200 response from API: {response} - {response.get('response_code')}"
                )
                break

            # Get the results and pagination data
            results = response.get(
                "results", []
            )  # throwing the 'NoneType' object has no attribute 'get'
            pagination = response.get("pagination", {})

            # if empty results array but successful GET => params is too strict
            if not results and str(response.get("response_code"))[0] == "2":
                # Try loosening search filters
                bad_keys.update(
                    {
                        key
                        for key, value in user_preferences_dict.items()
                        if value not in ["state", "country"]
                    }
                )

                # Fetch with less strict params
                new_prefs = {
                    key: value
                    for key, value in user_preferences_dict.items()
                    if key not in bad_keys
                }
                new_params = self.preprocess_preferences(
                    init_params_copy=init_params.copy(), prefs_obj=new_prefs
                )

                # Retry with new params
                response = self._get_request(
                    request_url="https://api.petfinder.com/v2/animals",
                    params=new_params,
                )
                print(f"RETRY API Response: {response.status_code} - {response.text}")

            # Filter results based on favorites
            if favorites:
                results = self.filter_favorites_by_id(
                    results=results,
                    favorites=favorites,
                    user_state=params.get("state"),
                    is_animal=True,
                )

            if results:
                # update the results key in response
                response["results"] = results
                # update the page key in response
                response["page"] = page

                if target_page is None or page == target_page:
                    yield response  # Yield the filtered results

            # Stop if no more pages to fetch
            total_pages = pagination.get("total_pages")
            if (
                page >= total_pages
                or (target_page is not None and page >= target_page)
                or not total_pages
            ):
                break

            # Increment the page number
            page += 1

    def get_mapped_animals_by_type(
        self,
        init_params,
        favorites,
        user_preferences_dict={},
        filter_prefs={},
    ):
        """function for generating PetFinder API results that are filtered and parsed/formatted."""

        pagination = self.animal_pagination_generator(
            init_params=init_params,
            favorites=favorites,
            user_preferences_dict=user_preferences_dict,
            target_page=init_params.get("page", 1),
        )
        try:
            page_data = next(pagination)
            print("generated API results=", page_data)
        except StopIteration:
            # Handle case where the requested page doesn't exist
            # Handle case where no results are found
            return {
                "filtered": [],
                "pagination": {},
                "results": [],
                "success_flag": False,
                "api_page": init_params.get("page", 1),
                "bad_keys": [],
                "message": "No results found",
            }

        # Split results by animal type
        split_dict_of_results = self.split_animals_by_type(
            animals=page_data.get("results", [])
        )

        filtered_results = []
        filtering_success = []
        combined_bad_keys = set()  # Use set to avoid duplicates

        # Iterate over each animal type and apply filters
        for animal_type, type_specific_filter_conditions in filter_prefs.items():
            type_specific_result_list = split_dict_of_results.get(
                animal_type.lower(), []
            )

            # Filter results for this animal type
            animal_type_filtering = self.filter_results_list(
                filter_conditions=type_specific_filter_conditions,
                results_list=type_specific_result_list,
            )

            # Logging for debugging
            print(
                "animal filtering",
                {
                    key: value
                    for key, value in animal_type_filtering.items()
                    if key != "results"
                },
            )

            # Combine bad_keys from each animal type filtering
            combined_bad_keys.update(animal_type_filtering.get("bad_keys", []))

            # Accumulate filtered results and update filtering success flag
            filtered_results += animal_type_filtering["results"]

            # Add the success_flags to the list (True if filtering was successful)
            filtering_success.append(animal_type_filtering.get("success_flag", False))

        # Determine if filtering was successful for any animal type
        final_filtering_success = any(filtering_success)

        # If no filtered results, fallback to initial unfiltered results
        if not filtered_results:
            parsed_and_filtered = parse_multi_animal(
                animal_list=page_data["results"]
            )  # Fallback to unfiltered parsing
        else:
            # Parse filtered results
            parsed_and_filtered = parse_multi_animal(animal_list=filtered_results)

        # Return the current page results with combined flags and parsed results
        return {
            "filtered": final_filtering_success,
            "pagination": page_data.get("pagination"),
            "results": parsed_and_filtered,
            "success_flag": final_filtering_success
            and bool(parsed_and_filtered),  # Ensure non-empty results
            "api_page": page_data.get("page"),  # return API page number
            "bad_keys": list(combined_bad_keys),  # Convert set to list for return
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

    def filter_favorites_by_id(results, favorites, user_state=None, is_animal=True):
        """
        Filters out results (either animals or organizations) that have IDs present in the user's favorites list.

        Args:
            results (list): List of animal/organization objects from the API.
            favorites (list): Sorted list of favorite animal or organization IDs.
            user_state (str): User's state abbreviation (optional, for organization filtering).
            is_animal (bool): Flag to indicate whether filtering is for animals or organizations.

        Returns:
            list: Filtered results excluding those present in the favorites list or,
                for organizations, those outside the user's state.
        """

        def binary_search(sorted_list, target):
            """Helper function to perform binary search on a sorted list."""
            low, high = 0, len(sorted_list) - 1
            while low <= high:
                mid = (low + high) // 2
                if sorted_list[mid] == target:
                    return True
                elif sorted_list[mid] < target:
                    low = mid + 1
                else:
                    high = mid - 1
            return False

        filtered_results = []
        favorites.sort()  # Ensure the favorites list is sorted for binary search

        for result in results:
            if is_animal:
                # Animal filtering logic
                animal_id = result.get("id")
                if isinstance(animal_id, int) and binary_search(favorites, animal_id):
                    continue  # Skip if the animal ID is in the favorites list
            else:
                # Organization filtering logic
                org_id = result.get("id")
                if isinstance(org_id, str) and user_state:
                    state_part = org_id[:2]  # Extract the state part from the org ID
                    number_part = org_id[2:]  # Extract the integer part

                    if state_part != user_state:
                        continue  # Skip organizations not matching the user's state

                    try:
                        org_number = int(
                            number_part
                        )  # Convert the number part to an integer
                        if binary_search(favorites, org_number):
                            continue  # Skip if the organization number is in the favorites list
                    except ValueError:
                        continue  # If the org ID number part isn't valid, skip it

            # If the result isn't filtered out, add it to the filtered list
            filtered_results.append(result)

        return filtered_results
