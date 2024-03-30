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
    petpy_api_instance = Petfinder(
        key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET")
    )
    auth_token = petpy_api_instance._authenticate()
    auth_token_time = None  # not sure this should be stored in the class

    def get_authentication_token(self):
        """
        method to query PetFinder API for an authentication token that is required to access API
        """
        try:
            response = self.petpy_api_instance._authenticate()
        finally:
            data = response.json()
            self.auth_token = data.access_token
            self.auth_token_time = (
                datetime.datetime.now()
            )  # store time of token to be determined later when a new token is required
            self.auth_token_expiry_time_in_seconds = data.expires_in
            return data

    @on_exception(expo, RateLimitException, max_tries=10)
    @limits(calls=50, period=1)
    @limits(calls=1000, period=86400)
    def validate_auth_token(self, jsonify_data):
        """Validate if auth_token is valid or if needs a new token
        
        RETURNS AUTH_TOKEN IF VALID 
        RETURNS FALSE IF NOT VALID

        Args:
            jsonify_data (_type_): JSON auth token data from PetFinder API
        """
        token_valid_duration_in_seconds = jsonify_data.expires_in or 3600
        current_time = datetime.datetime.now()
        expiry_time = self.auth_token_time + datetime.timedelta(seconds=token_valid_duration_in_seconds)

        if current_time > expiry_time or (
            abs((self.auth_token_time - current_time).total_seconds()) <= 3600
        ):
            # Token has expired or is about to expire within an hour
            # Reset stored token and token time
            self.auth_token = None
            self.auth_token_time = None

            # Get new token
            self.get_authentication_token()
            return False  # Token not valid, return False
            
        else:
            return jsonify_data.auth_token  # Token is valid, return the authentication token


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
