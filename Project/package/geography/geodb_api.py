
import requests
import os
from ratelimit import (
    limits,
    RateLimitException,
    sleep_and_retry,
)
from ...package.petfinder_types import UserLocationData

#Define API variables
api_key = os.environ.get("GEODB_API_KEY") or None
# Define limit for GeoDB Cities API; free plan limits to 1000 calls per day
API_CALLS_PER_DAY = 1000
TIME_PERIOD = 86400  # Time period in seconds (86400 seconds = 24 hours)
MAX_TRIES = 3  # Maximum number of retries for handling RateLimitException


class GeoDBHelper:
    """ a GeoDB helper class with functions to do the following features as functions:


    **Core Methods:**

    - **filter_places**: Filters cities by various criteria like name prefix and population.
    - **find_nearby_places**: Finds cities near a specified latitude and longitude.
    - **get_place_details**: Retrieves detailed information about a specific city.
    - **get_country_regions**: Lists all regions within a specified country.
    - **get_places_in_region**: Retrieves all cities within a specified region.
    - **get_countries_by_currency**: Lists countries using a specific currency.

    # Usage example:
    # geo_helper = GeoDBHelper()
    # cities = geo_helper.filter_places(name_prefix="San")
    """

    BASE_URL = "http://geodb-free-service.wirefreethought.com/v1/geo"
    HEADERS = {"x-rapidapi-key": api_key, "Content-Type": "application/json"}
    
    @limits(calls=50, period=30)  # Limit of 50 calls per second
    @limits(calls=API_CALLS_PER_DAY, period=TIME_PERIOD)  # Limit of 1000 calls per day
    def find_cities(
        self,
        name_prefix=None,
        country_ids=None,
        location=None,
        timezone=None,
        min_population=50_000,
    ):
        params = {
            "namePrefix": name_prefix,
            "countryIds": country_ids,
            "location": location,
            "timezone": timezone,
            "minPopulation": min_population,
        }
        response = requests.get(
            f"{self.BASE_URL}/cities", headers=self.HEADERS, params=params
        )
        return response.json()

    def find_nearby_places(self, geolocation, radius=10):
        latitude, longitude = ",".split(geolocation)
        params = {"latitude": latitude, "longitude": longitude, "radius": radius}
        response = requests.get(
            f"{self.BASE_URL}/cities/nearby", headers=self.HEADERS, params=params
        )
        return response.json()

    def get_place_details(self, city_id):
        response = requests.get(
            f"{self.BASE_URL}/cities/{city_id}", headers=self.HEADERS
        )
        return response.json()

    def get_country_regions(self, country_id):
        response = requests.get(
            f"{self.BASE_URL}/countries/{country_id}/regions", headers=self.HEADERS
        )
        return response.json()

    def get_places_in_region(self, region_id):
        response = requests.get(
            f"{self.BASE_URL}/regions/{region_id}/cities", headers=self.HEADERS
        )
        return response.json()

    def get_city_geolocation(self, params: UserLocationData) -> Optional[str]:
        """
        # Example usage
        
        params = UserLocationData(state="CA", country="US", city="San Francisco")
        geolocation = get_city_geolocation(params)
        if geolocation:
            print(geolocation)
        
        """
        base_url = "https://wft-geo-db.p.rapidapi.com/v1/geo/cities"
        headers = {
            "X-RapidAPI-Key": "YOUR_RAPIDAPI_KEY",  # Replace with your RapidAPI key
            "X-RapidAPI-Host": "wft-geo-db.p.rapidapi.com"
        }
        query_params = {
            "namePrefix": params['city'],
            "countryIds": params['country'],
            "regionCode": params['state']
        }

        response = requests.get(base_url, headers=headers, params=query_params)

        if response.status_code == 200:
            data = response.json()
            if data['data']:
                # Get latitude and longitude from the first result
                city_info = data['data'][0]
                latitude = city_info.get('latitude')
                longitude = city_info.get('longitude')
                return f"{latitude}, {longitude}"
        else:
            print(f"Error: {response.status_code} - {response.text}")

        return None
