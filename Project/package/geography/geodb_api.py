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

import requests
import os
from ratelimit import (
    limits,
    RateLimitException,
    sleep_and_retry,
)

#Define API
api_key = os.environ.get("GEODB_API_KEY") or None
# Define limit for GeoDB Cities API; free plan limits to 1000 calls per day
API_CALLS_PER_DAY = 1000
TIME_PERIOD = 86400  # Time period in seconds (86400 seconds = 24 hours)
MAX_TRIES = 10  # Maximum number of retries for handling RateLimitException


class GeoDBHelper:
    BASE_URL = "<http://geodb-free-service.wirefreethought.com/v1/geo>"
    HEADERS = {"x-rapidapi-key": api_key, "Content-Type": "application/json"}

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
