# from petpy import Petfinder
import os
from dotenv import load_dotenv
import time
import pandas as pd
import logging
import requests
from urllib.parse import urlparse, urljoin
from itertools import combinations
from random import random

from backoff import on_exception, expo
from ratelimit import (
    limits,
    RateLimitException,
    sleep_and_retry,
)
from collections.abc import Iterable

from Project.core import default_animal_params
from Project.utils.parse import Parse, parse_multi_animal
from petfinder.petfinder_types import AnimalReqParams, AnimalTypes, AnimalFeatures

from petfinder.api_exceptions import (
    PetFinderInvalidCredentialsError,
    PetFinderAccessDeniedError,
    PetFinderResourceNotFoundError,
    PetFinderInvalidMethod,
    PetFinderUnexpectedServerError,
    PetFinderInvalidParametersError,
    PetFinderLocationError,
)

# Configure logging
logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)


load_dotenv()

# Define limit for generator function to make API calls as PetFinder limits to 1000 calls per day
API_CALLS_PER_DAY = 1000
TIME_PERIOD = 86400  # Time period in seconds (86400 seconds = 24 hours)
MAX_TRIES = 3  # Maximum number of retries for handling RateLimitException


class PetFinderAPI:
    """
    API class with methods to store access PetFinder API and help functions to map user preference data to API search parameters
    """

    BASE_API_URL = os.environ.get("PETFINDER_API_URL", "https://api.petfinder.com/v2")
    if "https://" not in BASE_API_URL:
        BASE_API_URL = "https://" + BASE_API_URL

    # user prefs that map to search params
    search_param_keys = [
        "spayed_neutered",
        "house_trained",
        "declawed",
        "special_needs",
        "shots_current",
    ]
    animal_environment_keys = [
        "child_friendly",
        "dogs_friendly",
        "cats_friendly",
    ]
    # keys that are dynamically generated
    dynamic_animal_keys = [
        "breed",
        "coat",
        "color",
        "gender",
        "size",
        "personality",
        "age",
    ]

    animal_params_that_accept_multiple = [
        "breed",
        "size",
        "gender",
        "age",
        "coat",
        "status",
        "organization",
    ]

    # Initialize a set to keep track of invalid parameters across calls
    bad_keys_set = set()

    def __init__(self, *args, **kwargs):

        self.access_token = os.environ.get("ACCESS_TOKEN", None)
        self.token_expiration = os.environ.get("TOKEN_EXPIRATION", None)

        if not self.access_token or self._find_init_value(
            keys=["access_token", "TOKEN", "token"], args=args, kwargs=kwargs
        ):
            self._get_access_token()
        else:
            self.access_token = (
                self._find_init_value(
                    keys=["access_token", "TOKEN", "token"], args=args, kwargs=kwargs
                )
                or self._get_access_token()
            )
            self.token_expiration = (
                self._find_init_value(
                    keys=["expiration", "EXPIRATION", "token_expiration"],
                    args=args,
                    kwargs=kwargs,
                )
                or self._get_access_token()
            )

        self.bad_keys_set = (
            self._find_init_value(
                keys=["BAD_KEYS", "bad_keys", "invalid-params", "bad-params"],
                args=args,
                kwargs=kwargs,
            )
            or self.bad_keys_set
            or set()
        )

    ###########################    # Helper functions for error handling ############################################################################################################
    def handle_error_response(error):
        """Create a structured error response from an exception instance."""
        return {
            "error_title": getattr(error, "error_title", "Error"),
            "error_subtitle": getattr(error, "error_subtitle", ""),
            "error_message": getattr(
                error, "error_message", "An error occurred. Please try again later."
            ),
            "redirect_url": getattr(error, "redirect_url", "/"),
            "redirect_text": getattr(error, "redirect_text", "Back to Home"),
        }

    def handle_invalid_parameters_error(self, response, params):
        """
        Handles ERR-00002: Invalid parameters.
        Logs invalid parameters, adds them to a tracking set, and retries the request
        without invalid parameters.
        Args:
            response (dict): API error response data.
            params (dict): Original request parameters.
        Returns:
            dict: Response of retried request or error if retry fails.
        """
        # Extract the list of invalid parameters
        invalid_params_info = response.get("invalid-params", [])
        original_request_url = response.request.url or self.BASE_API_URL + "/animals"
        original_request_endpoint = urlparse(original_request_url).path

        # Collect invalid parameters and log each one
        for param_info in invalid_params_info:
            bad_param = param_info.get("path")
            self.bad_keys_set.add(bad_param)  # Add to tracking set

            self.log_error(
                f"Invalid parameter '{bad_param}': {param_info.get('message')}", 400
            )

            # Remove invalid parameters from the original request parameters
            params.pop(bad_param, None)

        # Retry the request with corrected parameters
        try:
            logger.info("Retrying request with corrected parameters...")
            corrected_response = self.request_with_retry(
                original_request_endpoint, original_request_url, params
            )
            return corrected_response
        except Exception as retry_error:
            logger.error(f"Retry failed: {retry_error}")
            return {"error": "Retry failed", "details": str(retry_error)}

    # helper logger
    def log_error(self, message, status_code=None):
        """Logs error messages with optional status code."""
        logger.error(f"{status_code if status_code else ''} {message}")

    def log_and_raise_for_status(self, response):
        """
        Checks the response for known errors, logs, and raises appropriate exceptions.

        Args:
            response (Response): The response object from the API.

        Raises:
            PetFinderLocationError: If there is an error related to the 'location' field.
            PetFinderInvalidParametersError: If there is an error with invalid query parameters.
            PetFinderInvalidCredentialsError: If the credentials are invalid.
            PetFinderAccessDeniedError: If access is denied.
            PetFinderResourceNotFoundError: If the resource is not found.
            PetFinderUnexpectedServerError: For server-side errors.
        """
        if response.status_code == 200:
            return

        json_response = response.json()
        error_type = json_response.get("type", "").split("/")[-1]

        (
            self.log_error(
                f" GET REQUEST @ {response.url} => status {response.status_code} error type => {error_type}"
            )
            if error_type
            else self.log_error(
                f" GET REQUEST @ {response.url} => status {response.status_code}"
            )
        )

        # Handle 400 errors with invalid parameters
        if response.status_code == 400:
            invalid_params = json_response.get("invalid-params", [])
            bad_keys = set()
            error_messages = []

            for invalid_param in invalid_params:
                bad_key = invalid_param.get("path")
                error_message = invalid_param.get("message", "Invalid parameter.")
                param_location = invalid_param.get("in")

                if bad_key:
                    bad_keys.add(bad_key)

                # Raise a location error if the invalid param relates to location in query
                if bad_key == "location" and param_location == "query":
                    raise PetFinderLocationError(
                        error_message=f"Location error: {error_message}"
                    )

                # Collect messages for other invalid query parameters
                elif param_location == "query":
                    error_messages.append(f"{bad_key}: {error_message}")

            # Raise InvalidParametersError if any bad query parameters were found
            if error_messages:
                raise PetFinderInvalidParametersError(
                    invalid_params=bad_keys, error_message="; ".join(error_messages)
                )

        # Handle other specific status codes with a dictionary mapping
        status_code_errors = {
            401: PetFinderInvalidCredentialsError(),
            403: PetFinderAccessDeniedError(),
            404: PetFinderResourceNotFoundError(),
            405: PetFinderInvalidMethod(),
            500: PetFinderUnexpectedServerError(),
            503: PetFinderUnexpectedServerError(),
        }

        # Raise error for specific status codes or default raise_for_status
        if response.status_code in status_code_errors:
            raise status_code_errors[response.status_code]
        else:
            response.raise_for_status()

    @sleep_and_retry
    @limits(calls=API_CALLS_PER_DAY, period=TIME_PERIOD)
    def _get_access_token(self):
        """Instance method to request a new access token from Petfinder API

        Raises:
            Exception: "Error getting access token @ URL {url}: {response.status_code} - {response.text}"

        Returns:
            access_token: PetFinder API access token
        """
        # # turn token_expiration into int if truthy
        # self.token_expiration = (
        #     int(self.token_expiration) if self.token_expiration else None
        # )

        # get current time
        current_time = int(time.time())

        # Check if valid token is stored in os.environ
        os_key = os.environ.get("ACCESS_TOKEN", None)
        os_key_expiration = os.environ.get("TOKEN_EXPIRATION", None)

        if (os_key and os_key_expiration) and current_time < int(os_key_expiration):
            self.access_token = os_key
            self.token_expiration = int(os_key_expiration)
            return os_key

        # Check if instance has a valid token
        if (self.access_token and self.token_expiration) and current_time < int(
            self.token_expiration
        ):
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
                self.token_expiration = int(current_time) + int(
                    token_info["expires_in"]
                )

                # save token & token_expiration to env variables
                os.environ["ACCESS_TOKEN"] = str(self.access_token)
                os.environ["TOKEN_EXPIRATION"] = str(self.token_expiration)

                print(
                    f"new access_token received PetFinderAPI and api instance updated {self.access_token}"
                )
                return self.access_token
            elif response.status_code == 500:
                time.sleep(2)  # Sleep for 2 seconds before retrying
            else:
                raise Exception(
                    f"Error getting access token @ URL {url}: {response.status_code} - {response.text}"
                )
        raise Exception(f"Failed to get access token after multiple attempts.")

    ### GET Request Functions #################################################################################################################################################################

    def _get_request(
        self,
        request_url,
        endpoint: str,
        params: AnimalReqParams = None,
    ) -> object:
        """Create a url to make an API request based off passed in params object.


        GET https://api.petfinder.com/v2/{CATEGORY}/?{parameter_1}={value_1}&{parameter_2}={value_2}

        Args:
            category (str): category of API to be called on eg. animal, animals, organization, organizations
            action(str): what REST request to make on API eg. 'get' = GET request
            params (OBJECT {str:str}): params Python OBJECT will be iterated on to create the key:value string queries to the url separated by question marks eg. `?{parameter_1}={value_1}`

        Returns:
            Response (object) requests Response object - to be handled in wrapper function or generator function
        """
        # handle if no params passed in, else format any list params within
        endpoint = endpoint if endpoint else "animals"
        request_url = request_url if request_url else f"{self.BASE_API_URL}/{endpoint}"

        params = self.format_list_params(params or {})

        # Obtain the current access token within the self._get_access_token() instead of helper petpy_api class
        access_token = self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        logger.info(
            f"_GET_REQUEST() @ {request_url} Params: <type ={type(params)}:{params}> Headers: {headers}"
        )

        # Make the GET request with the headers and params
        response = requests.get(request_url, params=params, headers=headers)
        return response

    def format_list_params(self, params: AnimalReqParams):
        """Validate and format parameters before making API requests."""
        formatted_params = {}
        for key, value in params.items():
            if isinstance(value, list) and key.lower() not in (
                self.animal_params_that_accept_multiple
                + [
                    "type",
                    "types",
                    "animal_type",
                    "animal_types",
                ]
            ):
                formatted_params[key] = ",".join(map(str, value))
            else:
                formatted_params[key] = value
        return formatted_params

    @on_exception(
        expo, RateLimitException, max_tries=MAX_TRIES
    )  # Exponential backoff retries
    @limits(calls=50, period=1)  # Limit of 50 calls per second
    @limits(calls=API_CALLS_PER_DAY, period=TIME_PERIOD)  # Limit of 1000 calls per day
    def request_with_retry(
        self,
        endpoint,
        request_url,
        params=default_animal_params,
        max_retries: int = MAX_TRIES,
    ):
        """
        Higher-order wrapper function that wraps the request in a retry mechanism to handle rate limits and temporary issues.

        This function sends a request to an endpoint with the option to retry a specified number of times.

        :param endpoint: The specific API endpoint path.
        :param request_url: Full URL for the API request.
        :param params: Dictionary of query parameters or data for the request.
        :param max_retries: Maximum retry attempts before raising an error.

        returns:
            tuple: (response.json(), response.status_code)(tuple)

        """
        if not isinstance(params, dict):
            raise TypeError(f"Expected 'params' as dict, received type: {type(params)}")

        for attempt in range(max_retries):
            response = self._get_request(
                endpoint=endpoint,
                request_url=request_url or f"{self.BASE_API_URL}/{endpoint}",
                params=params,
            )
            self.log_and_raise_for_status(
                response
            )  # Raise any appropriate errors based on response
            return response.json()  # Return if successful

    @on_exception(
        expo, RateLimitException, max_tries=MAX_TRIES
    )  # MAX_TRIES = max num of exponential retries before raising error
    @limits(calls=50, period=1)  # Limit of 50 calls per second
    @limits(calls=API_CALLS_PER_DAY, period=TIME_PERIOD)  # Limit of 1000 calls per day
    def _get_animal_types(self, *types):
        """
        Make a GET request to Petfinder API /types route.
        If types are provided, request specific animal types.
        """
        base_url = self.BASE_API_URL + "/types"

        if not types or types.lower() == "all":
            # If no types are specified, query all types
            result = self._get_request("types", request_url=base_url)
        else:
            # If types are specified, query each type individually
            if isinstance(types, (list, tuple, set)):
                results = []
                for animal_type in types:
                    type_url = f"{base_url}/{animal_type}"
                    response = self.request_with_retry("type", request_url=type_url)
                    result = response.get("results")
                    results.append(result)
                return results
            elif isinstance(types, str):
                url = type_url + f"/{types}"
                result = self._get_request("type", request_url=url)

        return result

    @sleep_and_retry
    @limits(calls=50, period=1)  # Limit of 50 calls per second
    @limits(calls=API_CALLS_PER_DAY, period=TIME_PERIOD)
    def seed_animal_types(self):
        """Util function that returns a list of animal types to be seeded in Flask session and os.environ"""
        default_prettified_list = Parse.get_default_prettified_animal_types()

        try:
            response = self._get_animal_types(types="all")
            response_status = response.get("status_code", 500)
            req_results = response.get("results", [])

            if response_status in [200, 201]:
                # Extract type names from the response
                type_list = [animal_type.get("name") for animal_type in req_results]
            else:
                # Use default list if API call fails
                type_list = default_prettified_list

        except Exception as e:
            # Use default list if an exception occurs
            type_list = default_prettified_list
            print(f"Error seeding animal info: {e}")

        return type_list or default_prettified_list

    @on_exception(
        expo, RateLimitException, max_tries=MAX_TRIES
    )  # MAX_TRIES = max num of exponential retries before raising error
    @limits(calls=50, period=1)  # Limit of 50 calls per second
    @limits(calls=API_CALLS_PER_DAY, period=TIME_PERIOD)  # Limit of 1000 calls per day
    def _get_breeds(self, animal_type="dog"):
        """
        Make a GET request to Petfinder API /breeds route.
        If animal_type is provided, request breeds for that specific type.
        """
        base_url = self.BASE_API_URL + "/breeds"

        if not animal_type:
            # If no animal_type is specified, return an error or all types (depending on API behavior)
            return self._get_request("types", request_url=base_url)
        else:
            # If animal_type is specified, query breeds for that type
            breeds_url = f"{base_url}/{animal_type}/breeds"
            return self._get_request("breeds", request_url=breeds_url)

    @on_exception(
        expo, RateLimitException, max_tries=MAX_TRIES
    )  # MAX_TRIES = max num of exponential retries before raising error
    @limits(calls=50, period=1)  # Limit of 50 calls per second
    @limits(calls=API_CALLS_PER_DAY, period=TIME_PERIOD)  # Limit of 1000 calls per day
    def _get_organizations(self, org_id=None, **params):
        """
        Make a GET request to Petfinder API /organizations route.
        If org_id is provided, request a specific organization.
        Additional parameters can be passed as keyword arguments.
        """
        base_url = "https://api.petfinder.com/v2/organizations"

        if org_id:
            # If org_id is specified, query that specific organization
            request_url = f"{base_url}/{org_id}"
            return self._get_request("organization", request_url=request_url, **params)
        else:
            # If no org_id is specified, query all organizations with optional params
            return self._get_request("organizations", request_url=base_url, **params)

    @on_exception(
        expo, RateLimitException, max_tries=MAX_TRIES
    )  # MAX_TRIES = max num of exponential retries before raising error
    @limits(calls=50, period=1)  # Limit of 50 calls per second
    @limits(calls=API_CALLS_PER_DAY, period=TIME_PERIOD)  # Limit of 1000 calls per day
    def _get_animals(self, animal_id=None, **params):
        """
        Make a GET request to Petfinder API /animals route.
        If animal_id is provided, request a specific animal.
        Additional parameters can be passed as keyword arguments.
        """
        base_url = "https://api.petfinder.com/v2/animals"

        if animal_id:
            # If animal_id is specified, query that specific animal
            request_url = f"{base_url}/{animal_id}"
            return self._get_request("animal", request_url=request_url, **params)
        else:
            # If no animal_id is specified, query all animals with optional params
            return self._get_request("animals", request_url=base_url, **params)

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
                if key in self.search_param_keys:
                    return (
                        lambda obj: obj.get("attributes", {}).get(key, False) == value
                    )
                elif key in self.animal_environment_keys:
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
                    if key in self.search_param_keys:
                        return (
                            lambda obj: obj.get("attributes", {}).get(key, False)
                            == True
                        )
                    elif key in self.animal_environment_keys:
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

    def preprocess_preferences(self, init_params, prefs_obj):
        """helper function to preprocess user prefs_obj and reduce if they include any values in excluded_values (ie. "any"/False)
        use this to create search params mapped to PetPy animals function parameter requirements

        Args:
            init_params (_type_): copy of init search params
            prefs_obj (dict): user preferences

        Returns:
            flattened_params (dict): search parameters or empty {}
        """
        # if prefs_obj is falsy, return empty object
        if not prefs_obj:
            return init_params if init_params else {}
        # prefs that only have true/false/None possibilities
        boolean_prefs = {
            bool_key: False
            for bool_key in self.animal_environment_keys + self.search_param_keys
        }

        # prefs that only have 'any' or a list possibilities
        any_prefs = {pref_key: ["any"] for pref_key in self.dynamic_animal_keys}

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
        mapped_search_params = init_params.copy()

        # Filter prefs_obj to remove any 'keys' that include an excluded value
        for key, value in prefs_obj.items():
            if isinstance(value, (str, bool)):  # handle booleans & string booleans
                if value not in excluded_values:
                    mapped_search_params[key] = value
            elif isinstance(
                value, (list, set, tuple)
            ):  # handle dynamic preferences in an iterable format
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
        search_params = mapped_search_params if mapped_search_params else init_params

        # Ensure proper query string encoding (flatten any complex structures) but exclude type/types/species as API does not accept multiples of those
        flattened_params = {
            key: (
                ",".join(value)
                if (isinstance(value, list) and key not in ("type", "types", "species"))
                else value
            )
            for key, value in search_params.items()
        }

        # # TODO: REMOVE LATER
        # # Debugging for visualization of params
        print(
            flattened_params,
            "=> flattened pre_processed_params being passed as params to /animals API call",
        )
        # flattened params should be a dict of strs, bool, and 1 list (which is type/types/species)
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
        animal_list =PetFinderAPI._get_request(url="/animals")

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

    @on_exception(
        expo, RateLimitException, max_tries=MAX_TRIES
    )  # Exponential backoff retries
    @limits(calls=50, period=1)  # Limit of 50 calls per second
    @limits(calls=API_CALLS_PER_DAY, period=TIME_PERIOD)  # Limit of 1000 calls per day
    def animal_pagination_generator(
        self,
        animal_types,
        next_urls,
        init_params,
        flattened_animal_preferences,
        exclude_ids=set(),
        target_count=10,
        location_dict=None,
    ):
        """
        Generator to fetch paginated animal results across multiple animal types.

        Args:
            animal_types (list): List of animal types to fetch results for.
            next_urls (dict): Dictionary containing next URLs for each animal type.
            init_params (dict): Initial parameters for the API request.
            flattened_animal_preferences (dict): Animal preferences to include in API requests.
            exclude_ids (set): Set of IDs to exclude (e.g., favorites or seen results).
            target_count (int): The number of results to yield.
            location_dict (dict): Dictionary containing location details for the request.

        Yields:
            list: Filtered animal data from the API, excluding results in exclude_ids.
            dict: The updated next_urls dictionary for tracking pagination.
        """
        yielded_results = []
        all_empty = False  # Start with False to initiate API requests on the first run

        # Combine initial parameters with animal preferences and location if provided
        params = init_params.copy()
        if flattened_animal_preferences:
            params.update(flattened_animal_preferences)

        if location_dict or isinstance(params.get("location"), (dict, object)):
            # set params['location'] properly
            params["location"] = self.get_next_location(location_dict=location_dict)

        # Initial fetch if next_urls are empty (first request scenario)
        if not any(next_urls.values()):
            try:
                for animal_type in animal_types:
                    # Set animal type in parameters and prettify the type for the API to accept it
                    params["type"] = Parse.prettify_animal_types(
                        animal_types=animal_type
                    )
                    request_url = f"{self.BASE_API_URL}/animals"
                    response_data = self.request_with_retry(
                        "animals", request_url, params=params
                    )

                    if response_data:
                        # Update next URL for pagination tracking
                        returned_next_url = (
                            response_data.get("pagination", {})
                            .get("_links", {})
                            .get("next", {})
                            .get("href", "")[3:]
                        )
                        next_urls[animal_type] = (
                            urljoin(self.BASE_API_URL, returned_next_url)
                            if returned_next_url
                            else None
                        )

                        filtered_results = self.filter_results_by_ids(
                            response_data.get("animals"), exclude_ids, is_animal=True
                        )
                        yielded_results.extend(filtered_results)

                        # Yield results if target count is reached
                        if len(yielded_results) >= target_count:
                            yield yielded_results, next_urls
                            return
            except Exception as e:
                # Log the error, yield whatever we have, and break the loop for this animal type
                self.log_error(
                    f"Error fetching data for {animal_type}, yielding partial results{filtered_results}: {e}"
                )
                yield {
                    "error": str(e),
                    "animal_type": animal_type,
                    "partial_results": filtered_results,
                }

        # Continue fetching until target_count is met or all pages are exhausted
        while len(yielded_results) < target_count:
            all_empty = True  # Reset all_empty each iteration

            for animal_type in animal_types:
                next_url = next_urls.get(animal_type)

                if not next_url:
                    continue  # Skip this type if no next URL is available (exhausted)

                # Fetch data from the API using request_with_retry
                response_data = self.request_with_retry(
                    endpoint="animals", request_url=next_url, params=params
                )

                if not response_data:
                    next_urls[animal_type] = (
                        None  # Mark as exhausted if no response received
                    )
                    continue

                # Update next URL for pagination tracking
                next_url = (
                    self.save_next_url(response_data.get("pagination"))
                    if "pagination" in response_data
                    else None
                )
                next_urls[animal_type] = next_url

                # Filter and accumulate results
                results = response_data.get("animals", [])
                filtered_results = self.filter_results_by_ids(
                    results, exclude_ids, is_animal=True
                )
                yielded_results.extend(filtered_results)

                # Yield results if target count is reached
                if len(yielded_results) >= target_count:
                    yield yielded_results, next_urls
                    return

            # Break the loop if no more pages are available across all animal types
            if all_empty:
                break

        # Yield remaining results if target count wasn't met
        yield yielded_results, next_urls

    ### FILTER FUNCTIONS ##################################################################################################################
    def filter_parse_animal_results(
        self,
        results,
        filter_prefs={},
    ):
        """
        Filters and parses a list of animal results based on user preferences.

        Args:
            results (list): List of animal result dictionaries to filter and parse.
            filter_prefs (dict): User preferences for filtering.

        Returns:
            tuple: (filtered results list, success flag)
        """
        # Early exit if results list is empty or invalid
        if not results or not isinstance(results, list):
            return [], False

        # Split results by animal type
        split_dict_of_results = self.split_animals_by_type(animals=results)

        filtered_results = []
        filtering_success = []

        # Apply filters for each animal type
        for animal_type, type_specific_filter_conditions in filter_prefs.items():
            type_specific_result_list = split_dict_of_results.get(
                animal_type.lower(), []
            )

            # Apply type-specific filters
            animal_type_filtering = self.filter_results_list(
                filter_conditions=type_specific_filter_conditions,
                results_list=type_specific_result_list,
            )

            # Accumulate filtered results and success flags
            filtered_results += animal_type_filtering["results"]
            filtering_success.append(animal_type_filtering.get("success_flag", False))

        # Determine if filtering was successful for any type
        final_filtering_success = any(filtering_success)

        # Fallback to initial unfiltered results if all items were filtered out
        if not filtered_results or not final_filtering_success:
            return {"results": [], "success_flag": False}
        else:
            # Parse only the filtered results
            parsed_and_filtered = parse_multi_animal(animal_list=filtered_results)

        # Return parsed results list and the final success flag
        return parsed_and_filtered, final_filtering_success and bool(
            parsed_and_filtered
        )

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

    def filter_results_by_ids(results, exclude_ids, user_state=None, is_animal=True):
        """
        Filters out results (either animals or organizations) that have IDs present in the exclude_ids set.

        Args:
            results (list): List of animal/organization objects from the API.
            exclude_ids (set): Set of IDs to exclude (e.g., favorites or seen results).
            user_state (str): User's state abbreviation (optional, for organization filtering).
            is_animal (bool): Flag to indicate whether filtering is for animals or organizations.

        Returns:
            list: Filtered results excluding those present in the exclude_ids set or,
                for organizations, those outside the user's state.
        """
        filtered_results = []

        for result in results:
            result_id = result.get("id")

            # Skip if the ID is in exclude_ids
            if result_id in exclude_ids:
                continue

            # Additional filtering for organizations by state
            if not is_animal and user_state:
                state_part, number_part = result_id[:2], result_id[2:]

                if state_part != user_state:
                    continue

                # Ensure number_part is an integer if needed for exclude_ids matching
                try:
                    org_number = int(number_part)
                    if org_number in exclude_ids:
                        continue
                except ValueError:
                    continue

            # If result isn't filtered out, add it to filtered results
            filtered_results.append(result)

        return filtered_results

    def _find_init_value(self, keys, args, kwargs):
        """
        The `_find_init_value` function processes keys to find a value in kwargs or the first dictionary in args.

        :param keys: The `keys` parameter in the `_find_init_value` method is used to specify the keys that you
        want to search for in the `args` and `kwargs` parameters. These keys can be provided as a single
        string or as an iterable (e.g., list, tuple) of strings. The
        :param args: The `args` parameter in the `_find_init_value` method is expected to be a tuple containing
        the positional arguments passed to the method. In this method, it is checked whether the first
        element of `args` is a dictionary, and if it is, the method looks for the keys in that dictionary
        :param kwargs: Keyword arguments passed to the function
        :return: The `_find_init_value` method returns the value associated with the specified keys in the
        `kwargs` dictionary or the first dictionary in the `args` list. If the keys are not found in either
        `kwargs` or the first dictionary in `args`, it returns `None`.
        """

        processed_keys = self.process_keys(keys)

        # Check in kwargs
        for key in processed_keys:
            if key in kwargs:
                return kwargs[key]

        # Check in args if it's a dictionary
        if args and isinstance(args[0], dict):
            for key in processed_keys:
                if key in args[0]:
                    return args[0][key]

        return None

    def process_keys(self, keys):
        """
        The function `process_keys` takes a string or an iterable of keys and returns a list of lowercase
        keys.

        :param keys: The `keys` parameter in the `process_keys` function can be either a string or an
        iterable (e.g., list, tuple, set). The function processes the keys by converting them to lowercase
        and returning a list of lowercase keys. If the input `keys` is a string, it converts
        :return: The function `process_keys` is returning a list of lowercase keys. If the input `keys` is a
        string, it converts the string to lowercase and returns a list containing that lowercase string. If
        the input `keys` is an iterable (e.g., list, tuple), it converts each element to lowercase and
        returns a list of lowercase elements. If the input `keys` is neither a string
        """
        if isinstance(keys, str):
            return [keys.lower()]
        elif isinstance(keys, Iterable):
            return [key.lower() for key in keys]
        else:
            raise ValueError("Keys must be a string or an iterable")

    ### LOCATION PARAM HELPER FUNCTIONS ############################

    def get_next_location(self, location_dict):
        """
        Selects the next value from a location dictionary to retry a GET request
        with a different location parameter.

        :param location_dict: A dictionary containing location information
        :return: The next location value to use, or None if no more options are available
        """
        priority_order = [
            "geolocation",
            "postal_code",
            ("city", "state"),
            ("state", "country"),
            "country",
        ]

        for item in priority_order:
            if isinstance(item, tuple):
                if all(location_dict.get(key) for key in item):
                    return f"{location_dict[item[0]]}, {location_dict[item[1]]}"
            else:
                value = location_dict.get(item)
                if value:
                    return value

        return None

    def detect_location_param(self, location_string):
        """
        Detects the type of location parameter from a given string.

        :param location_string: A string representing a location
        :return: The detected location parameter type(s)
        """
        if "," in location_string:
            parts = location_string.split(",")
            if len(parts) == 2 and all(
                part.strip().replace(".", "").isdigit() for part in parts
            ):
                return ["geolocation"]
            elif len(parts) == 2 and all(len(part.strip()) == 2 for part in parts):
                return ["state", "country"]
            else:
                return ["city", "state"]
        elif location_string.isdigit() or (
            location_string[:1].isalpha() and location_string[1:].isdigit()
        ):
            return ["postal_code"]
        elif len(location_string) == 2 and location_string.isalpha():
            return ["country"]
        else:
            return ["city"]

    def get_alternative_locations(self, location_dict):
        """
        Gets the next location to try, updates the location dictionary by removing
        the used location parameter, and returns the next location to try.

        :param location_dict: A dictionary containing location information
        :return: A tuple containing the next location to try and the updated dictionary
        """
        next_location = self.get_next_location(location_dict)
        if next_location is None:
            return None, location_dict

        param_types = self.detect_location_param(next_location)

        # Create a copy of the dictionary to avoid modifying the original
        updated_dict = location_dict.copy()

        # Remove the used location parameter(s) from the dictionary
        for param_type in param_types:
            updated_dict.pop(param_type, None)

        return next_location, updated_dict

    def generate_location_combinations(self, location_dict):
        """
        Generate unique combinations of location options.

        Args:
            location_dict (dict of str): where the keys are the location options and the values are the corresponding string representations.

        Returns:
            list of tuples: A list where each tuple contains (key, value) pairs.
                            The key is a combination of option names (joined by underscores),
                            and the value is a string of the corresponding option values (joined by commas).
        """
        options = list(location_dict.keys())
        unique_combinations = set()

        # Generate all possible unique combinations
        for r in range(1, len(options) + 1):
            for combo in combinations(options, r):
                key = "_".join(sorted(combo))  # Sort to ensure uniqueness
                value = ",".join(location_dict[option] for option in sorted(combo))
                unique_combinations.add((key, value))

        # Convert set to list for easier handling
        result_combinations = list(unique_combinations)

        # Add specific examples if they don't already exist
        specific_combos = [
            ("country", location_dict.get("country", "")),
            (
                "city_state",
                f"{location_dict.get('city', '')},{location_dict.get('state', '')}",
            ),
            (
                "city_state_postal_code",
                f"{location_dict.get('city', '')},{location_dict.get('state', '')},{location_dict.get('postal_code', '')}",
            ),
            (
                "state_country",
                f"{location_dict.get('state', '')},{location_dict.get('country', '')}",
            ),
        ]

        for combo in specific_combos:
            if combo not in result_combinations and all(combo[1].split(",")):
                result_combinations.append(combo)

        return result_combinations

    def save_next_url(self, pagination_dict) -> str:
        """
        The function `save_next_url` extracts and concatenates the next URL from a pagination dictionary
        with a base API URL.

        :param pagination_dict: Pagination_dict is a dictionary containing information about pagination,
        typically retrieved from an API response. It may have a structure like this:
        :return: The `save_next_url` method returns a string that is the concatenation of the `BASE_API_URL`
        and the `href` value extracted from the `pagination_dict`. If the `href` value is not found or
        empty, it returns `None`.
        """
        returned_next_url = (
            pagination_dict.get("_links", {}).get("next", {}).get("href", "")[3:]
        )

        return f"{self.BASE_API_URL}{returned_next_url}" if returned_next_url else None


import time
import functools
from datetime import datetime, timedelta

# Define constants
API_CALLS_PER_DAY = 1000
TIME_PERIOD = 86400  # Time period in seconds (86400 seconds = 24 hours)
MAX_TRIES = 3  # Maximum number of retries for handling RateLimitException


class RateLimitException(Exception):
    pass


def dynamic_rate_limit(func):
    """
    Decorator to dynamically manage API rate limiting.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.calls_made += 1

        for attempt in range(MAX_TRIES):
            try:
                result = func(*args, **kwargs)

                # Update total_results if available in the API response
                if hasattr(result, "get") and result.get("pagination"):
                    wrapper.total_results = result["pagination"].get(
                        "total_count", wrapper.total_results
                    )

                sleep_time = calculate_sleep_time(
                    wrapper.total_results, wrapper.calls_made
                )
                print(f"Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

                return result

            except RateLimitException:
                if attempt < MAX_TRIES - 1:
                    print(
                        f"Rate limit hit. Retrying in 60 seconds... (Attempt {attempt + 1}/{MAX_TRIES})"
                    )
                    time.sleep(60)
                else:
                    print("Max retries reached. Sleeping until rate limit reset...")
                    sleep_until_reset()

        raise Exception("Failed to make API call after maximum retries")

    wrapper.calls_made = 0
    wrapper.total_results = float(
        "inf"
    )  # Initialize with infinity, will be updated with actual count
    return wrapper


def calculate_sleep_time(total_results, calls_made, buffer_factor=1.1):
    """
    Calculates the dynamic sleep time based on API usage and limits.
    """
    remaining_calls = API_CALLS_PER_DAY - calls_made

    if remaining_calls <= 0:
        return sleep_until_reset()

    time_until_reset = get_time_until_reset()

    if calls_made >= total_results:
        return time_until_reset

    sleep_time = (time_until_reset / remaining_calls) * buffer_factor
    return max(1, min(sleep_time, 3600))  # Between 1 second and 1 hour


def get_time_until_reset():
    """
    Calculates the time until the next rate limit reset.
    """
    now = datetime.now()
    next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        days=1
    )
    return (next_reset - now).total_seconds()


def sleep_until_reset():
    """
    Sleeps until the next rate limit reset.
    """
    sleep_time = get_time_until_reset()
    print(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds until reset.")
    time.sleep(sleep_time)
    return 0  # Return 0 as we've already slept


# Example usage
@dynamic_rate_limit
def make_api_call(endpoint):
    # Simulated API call
    print(f"Making API call to {endpoint}")
    # Simulate a rate limit exception occasionally
    if random.random() < 0.1:
        raise RateLimitException("Rate limit exceeded")
    return {
        "data": "Some data",
        "pagination": {
            "total_count": 9000  # This would be the actual total from the API
        },
    }


# Using the decorated function
for i in range(1100):  # Trying to make more calls than the daily limit
    try:
        result = make_api_call(f"/endpoint/{i}")
        print(f"Call {i + 1} successful")
    except Exception as e:
        print(f"Error on call {i + 1}: {str(e)}")
        break
