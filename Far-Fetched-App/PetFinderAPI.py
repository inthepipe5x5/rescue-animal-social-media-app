import os
import dotenv
import requests
import datetime
from ratelimit import limits, RateLimitException
from backoff import expo, on_exception

from petpy import Petfinder


class PetFinderPetPyAPI:
    """
    API class with methods to store access PetFinder API
    """

    BASE_API_URL = os.environ.get("PETFINDER_API_URL", "https://api.petfinder.com/v2")
    if "https://" not in BASE_API_URL:
        BASE_API_URL = "https://" + BASE_API_URL

    def __new__(cls):
        cls.petpy_api_instance = Petfinder(
            key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET")
        )
        cls.auth_token_time = datetime.datetime.now()
        cls.validate_auth_token(cls.petpy_api_instance._auth)

    def get_authentication_token(self):
        """
        method to query PetFinder API for an authentication token that is required to access API
        """
        try:
            response = (
                self.petpy_api_instance._authenticate()
            )  # might be redundant as petpy_api_instance calls this function on authentication
        finally:
            data = response.json()
            self.auth_token = data.access_token
            self.auth_token_time = ()  # store time of token to be determined later when a new token is required
            self.auth_token_expiry_time_in_seconds = data.expires_in
            return data

    @on_exception(expo, RateLimitException, max_tries=10)
    @limits(calls=50, period=1)
    @limits(calls=1000, period=86400)
    def validate_auth_token(self, jsonify_data):
        """Validate if auth_token is valid or if a new token is needed.

        Returns:
            AUTH_TOKEN if valid.
            False if not valid.

        Args:
            jsonify_data (dict): JSON auth token data from PetFinder API.
        """
        if not isinstance(jsonify_data, dict):
            raise TypeError("jsonify_data must be a dictionary.")

        try:
            token_valid_duration_in_seconds = jsonify_data.get("expires_in", 3600)
            current_time = datetime.datetime.now()
            expiry_time = self.auth_token_time + datetime.timedelta(
                seconds=token_valid_duration_in_seconds
            )

            if (
                current_time > expiry_time
                or abs((self.auth_token_time - current_time).total_seconds()) <= 3600
            ):
                # Token has expired or will expire within the next hour
                self.auth_token = None
                self.auth_token_time = None
                self.get_authentication_token()  # Get a new token
                return self.auth_token
            else:
                return jsonify_data.get("auth_token")
        except Exception as e:
            # Handle any exceptions here
            print("An error occurred:", e)
            return False
        finally:
            # Code here will always execute, regardless of whether an exception occurred or not
            print("Validation of auth token completed.")

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

    def get_init_df_of_animal_rescue_organizations_by_distance_location(
        self,
        distance=100,
        location="Toronto, Ontario",
        sortBool=True,
        return_df_bool=True,
    ):
        """Get DataFrame of animal rescue organizations within a specified distance of a location.

        Args:
            distance (int, optional): Search parameter for results within this distance of the specified location. Defaults to 100 miles.
            location (str, optional): Specified location. Defaults to 'Toronto, Ontario'.
            sortBool (bool, optional): Boolean value for sorting results. Defaults to True.

        Returns:
            pandas.DataFrame: DataFrame of animal rescue organizations.
        """
        if not location or not distance:
            raise TypeError(
                f"Invalid location or distance parameters: {distance}, {location}"
            )

        try:
            init_orgs_df = self.petpy_api_instance.organizations(
                location=location,
                distance=distance,
                query=location,  # Search matching and partially matching name, city, or state.
                sort=sortBool,
                return_df=return_df_bool,
            )

            return init_orgs_df
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
