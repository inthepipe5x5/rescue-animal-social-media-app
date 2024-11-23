import fuzzywuzzy
import requests
import os
from ratelimit import (
    limits,
)

from Project.services.geography.util import GeoUtil
from Project.core.types import UserLocationData
from typing import List, Optional, Union


class GeoDB(GeoUtil):
    """a GeoDB helper class with functions to do the following features as functions:

    **Core Methods:**

    - **filter_places**: Filters cities by various criteria like name prefix and population.
    - **find_nearby_places**: Finds cities near a specified latitude and longitude.
    - **get_place_details**: Retrieves detailed information about a specific city.
    - **get_country_regions**: Lists all regions within a specified country.
    - **get_places_in_region**: Retrieves all cities within a specified region.
    - **get_countries_by_currency**: Lists countries using a specific currency.

    # Usage example:
    # geo_helper = GeoDB()
    # cities = geo_helper.filter_places(name_prefix="San")
    """

    # Define API variables
    api_key = os.environ.get("GEODB_API_KEY") or None
    # Define limit for GeoDB Cities API; free plan limits to 1000 calls per day
    API_CALLS_PER_DAY = 1000
    TIME_PERIOD = 86400  # Time period in seconds (86400 seconds = 24 hours)
    MAX_TRIES = 3  # Maximum number of retries for handling RateLimitException

    BASE_URL = "http://geodb-free-service.wirefreethought.com/v1/geo"
    HEADERS = {"x-rapidapi-key": api_key, "Content-Type": "application/json"}

    @limits(calls=50, period=30)  # Limit of 50 calls per second
    @limits(calls=API_CALLS_PER_DAY, period=TIME_PERIOD)  # Limit of 1000 calls per day
    def find_cities(
        self,
        name_prefix=None,
        country_ids=None,
        location=None,
        min_population=50_000,
    ):
        params = {
            "namePrefix": name_prefix,
            "countryIds": country_ids,
            "location": location,
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


    @staticmethod
    def get_city_details(self, city_identifier: Union[str, int], country):
        """
        This function retrieves details about a place based on the provided city ID or city name.

        :param city_identifier: Can be either a city ID (int) or a city name (str) for fuzzy search
        :return: A dictionary containing place details or None if not found
        """
        if isinstance(city_identifier, int):
            # If it's an integer, assume it's a city ID
            response = self.get_place_details(city_id=city_identifier)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return None
        elif isinstance(city_identifier, str):
            params = {"namePrefix": city_identifier, "countryIds": country}
            response = requests.get(
                f"{self.BASE_URL}/cities", headers=self.HEADERS, params=params
            )
            data = response.json()

            # Extract relevant information from API response
            city_info = data["data"][0] if data["data"] else None

            if city_info:
                return city_info
            return None
        else:
            print(
                "Invalid input. Please provide either a city ID (int) or a city name (str)."
            )
            return None

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

        query_params = {
            "namePrefix": params["city"],
            "countryIds": params["country"],
            "regionCode": params["state"],
        }

        response = requests.get(
            self.BASE_URL, headers=self.HEADERS, params=query_params
        )

        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                # Get latitude and longitude from the first result
                city_info = data["data"][0]
                latitude = city_info.get("latitude")
                longitude = city_info.get("longitude")
                return f"{latitude},{longitude}"
        else:
            print(f"Error: {response.status_code} - {response.text}")

        return None

    def get_cities_within_radius(self, location: str, radius: int) -> List[dict]:
        """
        Returns a list of cities within the specified radius of the given location.

        Args:
            location (str): Can be one of the following:
                - "country,state" (e.g., "US,CA")
                - "postal_code" (e.g., "90210")
                - "latitude,longitude" (e.g., "34.0522,-118.2437")
            radius (int): Search radius in miles

        Returns:
            List[dict]: A list of dictionaries containing city information
        """
        # Convert radius from miles to kilometers (GeoDB uses km)
        radius_km = radius * 1.60934

        # Determine the type of location input
        if "," in location and not location.replace(",", "").replace(".", "").isdigit():
            # It's a country,state format
            country, state = location.split(",")
            geolocation = self.get_state_geolocation(country.strip(), state.strip())
        elif location.replace(",", "").replace(".", "").isdigit():
            # It's a latitude,longitude format
            geolocation = location
        else:
            # Assume it's a postal code
            geolocation = self.get_postal_code_geolocation(location)

        if not geolocation:
            return []

        # Use the find_nearby_places method to get cities within the radius
        nearby_places = self.find_nearby_places(geolocation, radius_km)
        return nearby_places.get("data", [])

    def convert_state_to_geolocation_str(
        self, country: str, state: str
    ) -> Optional[str]:
        """
        Returns the geolocation (latitude,longitude) for a given state and country.

        Args:
            country (str): Country code (e.g., "US")
            state (str): State/province/territory code (e.g., "CA")

        Returns:
            Optional[str]: Geolocation as "latitude,longitude" or None if not found
        """
        params = {"countryIds": country, "regionCode": state, "types": "REGION"}
        response = requests.get(
            f"{self.BASE_URL}/places", headers=self.HEADERS, params=params
        )

        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                region_info = data["data"][0]
                latitude = region_info.get("latitude")
                longitude = region_info.get("longitude")
                return f"{latitude},{longitude}"
        else:
            print(f"Error: {response.status_code} - {response.text}")

        return None

    def convert_postal_code_to_geolocation_str(self, postal_code: str) -> Optional[str]:
        """
        Returns the geolocation (latitude,longitude) for a given postal code.

        Args:
            postal_code (str): Postal code

        Returns:
            Optional[str]: Geolocation as "latitude,longitude" or None if not found
        """
        params = {"postalCode": postal_code, "types": "CITY"}
        response = requests.get(
            f"{self.BASE_URL}/places", headers=self.HEADERS, params=params
        )

        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                city_info = data["data"][0]
                latitude = city_info.get("latitude")
                longitude = city_info.get("longitude")
                return f"{latitude},{longitude}"
        else:
            print(f"Error: {response.status_code} - {response.text}")

        return None

    @staticmethod
    def alternate_cities(city_dict: dict, country: str) -> List[dict]:
        """
        This function alternate_cities takes a dictionary of cities and a country name,
        and returns a list of dictionaries. Each dictionary contains country, state, and city
        information. The cities are alternated across all states/provinces.

        :param city_dict: A dictionary where keys are states/provinces and values are lists of cities
        :param country: The name of the country (e.g., "USA", "Canada")
        :return: A list of dictionaries with country, state, and city information

        # Example usage:
        # alternated_cities = alternate_cities(usa, "USA")
        # print(alternated_cities)
        """
        # Get the maximum length of any list in the dictionary
        max_len = max(len(cities) for cities in city_dict.values())

        result = []

        # Iterate through each index
        for i in range(max_len):
            # For each state/province, get the i-th city if it exists
            for state, cities in city_dict.items():
                if i < len(cities):
                    result.append(
                        {"country": country, "state": state, "city": cities[i]}
                    )

        return result
