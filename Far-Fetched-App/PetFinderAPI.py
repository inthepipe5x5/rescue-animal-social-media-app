import os
import dotenv
from flask import Flask, jsonify
import requests
import datetime

class PetFinderAPI():
    """
    API class with methods to store access PetFinder API
    """
    BASE_API_URL = os.environ.get("PETFINDER_API_URL","https://api.petfinder.com/v2")
    if "https://" not in BASE_API_URL:
        BASE_API_URL = "https://"+BASE_API_URL
        
    auth_token = None 
    auth_token_time = None #not sure this should be stored in the class
    
    def get_authentication_token(self):
        """
        method to query PetFinder API for an authentication token that is required to access API
        """
        headers = {
            "Authorization": "BEARER" + " " + os.environ.get('API_KEY', "/")
        }

        response = requests.get(self.BASE_API_URL,headers=headers)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Convert the response JSON data to a Python dictionary
            data = response.json()
            self.auth_token = data.access_token
            self.auth_token_time = datetime.now() #store time of token to be determined later when a new token is required
            return jsonify(data)
        elif response.status_code == 403: #403 is "Access denied due to insufficient access"
            self.get_authentication_token()
        else:
            # If the request was not successful, return an error message
            return jsonify({'error': 'Failed to fetch data'}), 500
    
    def validate_auth_token(self,jsonify_data):
        """Validate if auth_token is valid or if needs a new token

        Args:
            jsonify_data (_type_): JSON auth token data from PetFinder API 
        """
        current_time = datetime.now()
        
        if abs((self.auth_token_time - current_time).total_seconds()) <= 3600: #checks if token has expired by comparing delta of token received time to current time
            #reset stored token and token time
            self.auth_token = None
            self.auth_token_time = None
            
            #get new token
            self.get_authentication_token()
        
        else: 
            return jsonify_data 
    
    def create_custom_url_for_api_request(self, category, action, params):
        """Create a url to make an API request based off passed in params object. 
        
        
        GET https://api.petfinder.com/v2/{CATEGORY}/{ACTION}?{parameter_1}={value_1}&{parameter_2}={value_2}

        Args:
            category (str): category of API to be called on eg. animal, animals, organization, organizations
            action(str): what REST request to make on API eg. 'get' = GET request
            params (OBJECT {str:str}): params Python OBJECT will be iterated on to create the key:value string queries to the url separated by question marks eg. `?{parameter_1}={value_1}`
        """

        #WRITE CODE HERE     
        pass
    
    
    def get_animals_by_type(self):
        """GET method to get types of animals available from PetFinder API
        """
        
        #WRITE CODE HERE     
        pass
    
    