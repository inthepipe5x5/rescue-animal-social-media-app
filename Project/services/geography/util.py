import pycountry
from itertools import combinations
from urllib.parse import urljoin
from core import GeoLocationType, UserLocationData


class GeoUtil:
    """Utility class and methods for handling geography and location data"""

    def lookup_country(search_string: GeoLocationType.country) -> list:
        """
        The `lookup_country` function takes a search string and returns a list of dictionaries containing
        country objects that match the fuzzy search.

        :param search_string: The `lookup_country` function takes a `search_string` as input and returns a
        list of dictionaries containing information about countries that match the search string using fuzzy
        search. The `search_string` parameter is the string that will be used to search for countries
        :return: A list of dictionaries containing information about countries that match the search string
        using fuzzy search.
        """

        return [
            dict(country_obj)
            for country_obj in pycountry.countries.search_fuzzy(search_string)
        ]

    ### LOCATION PARAM HELPER FUNCTIONS ############################

    def get_next_location(self, location_dict: UserLocationData):
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

    def detect_location_param(self, location_string: str):
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
        print(result_combinations)
        return result_combinations


if __name__ == "__main__":
    geo = GeoUtil()
    location_dict = {
        "geolocation": "43.6429,-79.3889",
        "state": "ON",
        "country": "CA",
        "postal_code": "m5j0b3",
        "city": "Toronto",
    }
    print(geo.generate_location_combinations(location_dict=location_dict))
