import os
from dotenv import load_dotenv
import datetime
import requests

import pandas as pd
from flask import sessions
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
        "location": "Toronto, ON",
        "state": "ON",
        # "city": "Toronto",
        "country": "CA",
        "animal_types": ["dog"], #6 possible values:  ‘dog’, ‘cat’, ‘rabbit’, ‘small-furry’, ‘horse’, ‘bird’, ‘scales-fins-other’, ‘barnyard’.
        # "distance": 100,
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

    def __init__(self):
        print(os.environ.get("API_KEY"), os.environ.get("API_SECRET"))
        self.petpy_api = Petfinder(
            key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET")
        )
        self.auth_token_time = datetime.datetime.now()
        self.breed_choices = self.petpy_api.breeds()

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

    def get_animals_df(self, params_obj):
        """Get DataFrame of animal rescue organizations within a specified distance of a location.

        Args:
            params_obj (DICT) dictionary of search parameters
        Returns:
            pandas.DataFrame: DataFrame of animal rescue organizations.
        """
        try:
            # animal_types = params_obj.get("animal_types", [])

            # Fetch data from API
            animals_df = self.petpy_api.animals(**params_obj)
            animal_types = params_obj.get("animal_types")
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
        user_preferences = UserAnimalPreferences.query.get_or_404(
            User.id == user_id
        ).all()
        matching_animals = self.petpy_api.animals(
            type=animal_type_preferences,
            species=species_preference,
            breeds=breeds_preference,
            location=list_of_orgs,
        )

        return matching_animals


    def animals_df_to_org_animal_count_dict(self, animals_df):
        """Function to group animals DataFrame by 'organization_id' and count the number of animals in each group, sorted by count in descending order, and return the result as a dictionary.

        Args:
            animals_df (DataFrame): pandas DataFrame of animals API results
        """

        # Group by 'organization_id' and count the number of animals in each group
        organization_counts = (
            animals_df.groupby("organization_id").size().reset_index(name="animal_count")
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
    
    def parse_breed(breeds_obj):    
        """Function to parse breeds object property in a single Animal result from PetFinder API results"""    
        if not breeds_obj or breeds_obj.primary == False:    
            return 'Super Mutt' #breed is Super Mutt by default
        
        primary = breeds_obj.get('primary', '')    
        secondary = breeds_obj.get('secondary', False)    
        mixed_bool = breeds_obj.get('mixed', False)    
        unknown_bool = breeds_obj.get('unknown', False)
        
        if unknown_bool:        
            return 'Super Mutt'
        if mixed_bool:        
            if secondary:            
                return f"{primary} {secondary} mix"        
            else:            
                return f"{primary} Mix"    
        else:        
            return primary
    
    def parse_color(colors_obj):
        """Parse the colors object in an animal data object returned from API to remove false or null values"""
        
        if not colors_obj or colors_obj.primary == False:    
            return 'Unknown Color' #color is Unknown Color by default
        
        primary = colors_obj.get('primary', '')    
        secondary = colors_obj.get('secondary', False)    
        tertiary = colors_obj.get('tertiary', False)    
        
        if tertiary:        
            if secondary:            
                return f"{primary}, {secondary}"        
            else:            
                return f"{primary}"    
        else:        
            return primary
    def parse_photos(photos_list, type):    
        """Function to parse breeds object property in API results"""   
        
        #handle invalid or empty types
        if type not in ['dog', 'cat', 'horse', 'bird', 'rabbit', 'small-furry', 'barn-yard', 'scales-fins-other']:
            type = 'misc'
        
        #dictionary of urls for the graphics 
        default_animal_graphic = {
            "dog": "../static/images/graphics/dog-freepik.png",
            "cat": "../static/images/graphics/cat-freepik.png",
            "horse": "../static/images/graphics/horse-freepik.png",
            "bird": "../static/images/graphics/bird-eucalyp.png",
            "small-furry": "../static/images/graphics/small-furry-freepik.png",
            "scales-fins-other": "../static/images/graphics/scales-smashicons.png",
            "barnyard": "../static/images/graphics/scales-smashicons.png",
            "rabbit": "../static/images/graphics/rabbit-freepik.png",
            'misc': "../static/images/graphics/tracks_freepik.png"        
        }
        
        
        if not photos_list or len(photos_list) == 0:       
            return default_animal_graphic[type] #return default graphic if the animal has no photos
        else:
            return photos_list[0].get('full')

    def parse_location_obj(loc_obj):
        """Function to parse location object property in API results"
            if not loc_obj:
                    return """
        city = loc_obj.get('city', False)	
        state=loc_obj.get('state', False)
        country= loc_obj.get('country', False)	
        if city:
            if state:
                return {
                        "location":"".join(city, state.slice(0,1).upper()),
                        "state": state, 
                        "country": country, 
                        "city": city
                        }
        
        else:
            if state:
                return {
                        "location":"".join(state, country),
                        "state": state, 
                        "country": country, 
                        }
            else:
                return {
                        "location":"".join(country),
                        "country": country, 
                        }

    def parse_publish_date (pub_date, action='delta'):
        """Parse the published_date property in animal data object returned from API

        Args:
            pub_date (STRING): string date value returned from API
            action (STRING): the desired action to be done to the pub_date
                'delta' = get the difference between the pub_date and now()
                'format' = format the pub_date into a readable form
        """
        if action not in ['delta', 'format']:
            return TypeError('Wrong Action Type')
        
        if not pub_date:
            return None
        
        else:
            # Using current time
            today = datetime.now()
            #parse pub_date into datetime object
            date_obj = datetime.fromisoformat(pub_date.replace("+0000", ""))

            parsed_date = None
            
            #handle if action = 'delta'
            if action == 'delta':
                date_diff = today - date_obj
                #get the difference in days
                parsed_date = date_diff.days
                return parsed_date
                
            #handle if action = 'format'
            if action == 'format':
                parsed_date = date_obj.strftime("%d/%m/%Y")
                return parsed_date
    
    def parse_api_data(self, api_data):
        """
        Function to clean up missing data from api to be used in jinja templates
        
        Args:
            api_data (json): API data to be cleaned up and turned into content for JINJA templates
        """
        #output list of parsed animals
        parsed = []
        
        for animal in api_data:
            #parse the nested animal property objects 
            animal.breed = self.parse_breed(breed_obj=animal.breeds)
            animal.color = self.parse_color(color_obj=animal.colors)
            animal.photos = self.parse_photos(photo_list = animal.photos, type = animal.type)
            animal.location = self.parse_location_obj(loc_obj = animal.contact)
            animal.published_date = self.parse_publish_date(pub_date = animal.published_date, action='format')
            animal.date_delta_num = self.parse_publish_date(pub_date = animal.published_date, action='delta')
            
            #remove videos
            if 'videos' in animal:
                del animal['videos'] 
            parsed.append(animal)
        
        #return final list of parsed animals
        return parsed


pf_api = PetFinderPetPyAPI()
