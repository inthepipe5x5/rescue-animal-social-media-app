import os
from dotenv import load_dotenv
import requests
import datetime
from ratelimit import limits, RateLimitException
from backoff import expo, on_exception
from models import User#, #UserPreferences
from petpy import Petfinder

load_dotenv()

class PetFinderPetPyAPI():
    """
    API class with methods to store access PetFinder API
    """

    BASE_API_URL = os.environ.get("PETFINDER_API_URL", "https://api.petfinder.com/v2")
    if "https://" not in BASE_API_URL:
        BASE_API_URL = "https://" + BASE_API_URL

    def __init__(self):
        print('test string 123')
        print(
            os.environ.get("API_KEY"), os.environ.get("API_SECRET")
        )
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

    def get_init_rescue_organizations(
        self,
        distance=100,
        location="Toronto, Ontario",
        sortFilter="distance",
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
            init_orgs_df = self.petpy_api.organizations(
                location=location,
                distance=distance,
                query=location,  # Search matching and partially matching name, city, or state.
                sort=sortFilter,
                return_df=return_df_bool,
                count=100
            )

            return init_orgs_df
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        
    def map_user_preferences(self, user_preferences):
        """
        Function to map user preferences to a dictionary object.

        Args:
            user_preferences (UserPreferences): UserPreferences object containing user preferences.

        Returns:
            dict: Dictionary containing mapped user preferences.
        """
        mapped_preferences = {}
        
        # Extract the necessary preferences from the user_preferences object
        #mandatory preferences
        
        mapped_preferences['location_preference'] = user_preferences.location_preference if user_preferences.location_preference else []
        mapped_preferences['distance_preference'] = user_preferences.distance_preference if user_preferences.distance_preference else []
        mapped_preferences['status_preference'] = user_preferences.rescue_interaction_type_preference if user_preferences.rescue_interaction_type_preferences_preference else []
        mapped_preferences['specific_animal_type_preferences'] = user_preferences.specific_animal_type_preferences if user_preferences.specific_animal_type_preferences else []
        
        mapped_preferences['species_preference'] = user_preferences.species_preference if user_preferences.species_preference else []
        
        #optional preferences
        mapped_preferences['breeds_preference'] = user_preferences.breeds_preference if user_preferences.breeds_preference else []
        
        # Other preferences...

        return mapped_preferences
        

    def get_animals_as_per_user_preferences(self, list_of_orgs, user_id, animal_type_preferences, species_preference, breeds_preference):
        """Function that takes two args: list_of_orgs and a user_id and sends a GET request to PetFinder API for animals that match preferences from the user_id argument

        Args:
            list_of_orgs (ARR or Pandas DataFrame): list of organization IDs from API in a Python List (Array) or a Pandas DataFrame format.
            user_id (INT): id of user making search request (eg. the user_id stored in 'g' -> g.user_id)
        """

        user = User.query.get_or_404(User.id==user_id)
        user_preferences = UserPreferences.query.get_or_404(User.id==user_id)
        matching_animals = self.petpy_api.animals(
            type=animal_type_preferences,
            species=species_preference,
            breeds=breeds_preference,
            location=list_of_orgs,
        )

        return matching_animals

# pf_api = PetFinderPetPyAPI()