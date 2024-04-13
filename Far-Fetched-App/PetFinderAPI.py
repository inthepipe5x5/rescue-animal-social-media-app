import os
from dotenv import load_dotenv
import datetime
import requests

from flask import sessions
from ratelimit import limits, RateLimitException
from backoff import expo, on_exception
from petpy import Petfinder


from models import User  # , #UserPreferences

load_dotenv()


class PetFinderPetPyAPI:
    """
    API class with methods to store access PetFinder API and help functions to map user preference data to API search parameters
    """

    BASE_API_URL = os.environ.get("PETFINDER_API_URL", "https://api.petfinder.com/v2")
    if "https://" not in BASE_API_URL:
        BASE_API_URL = "https://" + BASE_API_URL
    
    #store default user_preference 
    default_options_obj = {
        "location": {"country": "CA", "city": "Toronto", "state": "ON"},
        "animal_types": ["dog", "cat"], #6 possible values:  ‘dog’, ‘cat’, ‘rabbit’, ‘small-furry’, ‘horse’, ‘bird’, ‘scales-fins-other’, ‘barnyard’.
        "distance": 100,
        "sort":'-recent',
        "count":100,
        "pages":4,
        'return_df': True
        # "custom": False
    } 

    def __init__(self):
        print("test string 123")
        print(os.environ.get("API_KEY"), os.environ.get("API_SECRET"))
        self.petpy_api = Petfinder(
            key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET")
        )
        self.auth_token_time = datetime.datetime.now()
        self.breed_choices = self.petpy_api.breeds()
        # self.validate_auth_token(token_data=self.petpy_api._auth)

    # def get_authentication_token(self):
    #     """
    #     method to query PetFinder API for an authentication token that is required to access API
    #     """
    #     try:
    #         response = (
    #             self.petpy_api._authenticate()
    #         )  # might be redundant as petpy_api calls this function on authentication
    #     finally:
    #         data = response.json()
    #         self.auth_token = data.access_token
    #         self.auth_token_time = ()  # store time of token to be determined later when a new token is required
    #         self.auth_token_expiry_time_in_seconds = data.expires_in
    #         return data

    # @on_exception(expo, RateLimitException, max_tries=10)
    # @limits(calls=50, period=1)
    # @limits(calls=1000, period=86400)
    # def validate_auth_token(self, token_data):
    #     """Validate if auth_token is valid or if a new token is needed.

    #     Returns:
    #         AUTH_TOKEN if valid.
    #         False if not valid.

    #     Args:
    #         token_data (dict): JSON auth token data from PetFinder API.
    #     """
    #     if not isinstance(token_data, dict):
    #         raise TypeError("token_data must be a dictionary.")

    #     try:
    #         token_valid_duration_in_seconds = token_data.get("expires_in", 3600)
    #         current_time = datetime.datetime.now()
    #         expiry_time = self.auth_token_time + datetime.timedelta(
    #             seconds=token_valid_duration_in_seconds
    #         )

    #         if (
    #             current_time > expiry_time
    #             or abs((self.auth_token_time - current_time).total_seconds()) <= 3600
    #         ):
    #             # Token has expired or will expire within the next hour
    #             return False
    #         else:
    #             return token_data
    #     except Exception as e:
    #         # Handle any exceptions here
    #         print("An error occurred:", e)
    #         return False
    #     finally:
    #         # Code here will always execute, regardless of whether an exception occurred or not
    #         print("Validation of auth token completed.")

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

    def get_orgs_df(self):
        """Get DataFrame of animal rescue organizations within a specified distance of a location.

        Args:
            distance (int, optional): Search parameter for results within this distance of the specified location. Defaults to 100 miles.
            location (str, optional): Specified location. Defaults to 'Toronto, Ontario'.
            sortBool (bool, optional): Boolean value for sorting results. Defaults to True.

        Returns:
            pandas.DataFrame: DataFrame of animal rescue organizations.
        """
        u_pref = sessions["user_preferences"]
        animal_types = u_pref.animal_types

        if u_pref.modified == True:
            pass
        else:
            u_pref = {**self.default_options_obj}
        try:
            del u_pref["animal_types"]
            init_orgs_df = self.petpy_api.organizations(**u_pref)
            # Filter DataFrame based on 'type' column
            filtered_df = init_orgs_df[init_orgs_df['type'].isin(animal_types)]
            return filtered_df
        except Exception as e:
            print(f"An error occurred while retrieving organizations: {e}")
            return None
    
    def get_animals_df(self, params_obj):
        """Get DataFrame of animal rescue organizations within a specified distance of a location.

        Args:
            params_obj (DICT) dictionary of search parameters
        Returns:
            pandas.DataFrame: DataFrame of animal rescue organizations.
        """
        try:
            animal_types = params_obj.get("animal_types", [])
            
            # Fetch data from API
            animals_df = self.petpy_api.animals(**params_obj)
            
            # Filter DataFrame based on 'animal_types'
            if animal_types:
                animals_df = animals_df[animals_df['type'].isin(animal_types)]
            
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
        mapped_data_obj = {**{key:value for key, value in form_data if form_data[key]}, **default_options_obj}

        return mapped_data_obj

    def get_animals_as_per_user_preferences(
        self,
        list_of_orgs,
        user_id,
        animal_type_preferences,
        species_preference,
        breeds_preference,
    ):
        """Function that takes two args: list_of_orgs and a user_id and sends a GET request to PetFinder API for animals that match preferences from the user_id argument

        Args:
            list_of_orgs (ARR or Pandas DataFrame): list of organization IDs from API in a Python List (Array) or a Pandas DataFrame format.
            user_id (INT): id of user making search request (eg. the user_id stored in 'g' -> g.user_id)
        """

        user = User.query.get_or_404(User.id == user_id)
        user_preferences = UserPreferences.query.get_or_404(User.id == user_id)
        matching_animals = self.petpy_api.animals(
            type=animal_type_preferences,
            species=species_preference,
            breeds=breeds_preference,
            location=list_of_orgs,
        )

        return matching_animals


pf_api = PetFinderPetPyAPI()
