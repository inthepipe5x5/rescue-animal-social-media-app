"""
Parser class to parse API results
"""

import datetime
import pytz
import pycountry
import json
import re
from copy import deepcopy
from collections.abc import Iterable


class ParsingError(Exception):
    """The ParsingError class will store the details of the error, including the original data, its type, and the parsing function that failed.

    Args:
        data (any): original data that needed to be parsed
        func_name (string): parsing function that failed
    """

    def __init__(self, data, func_name):
        self.data = data
        self.data_key = (
            data.__name__
        )  # key name of data being parsed within Data object
        self.func_name = func_name
        self.data_type = type(data).__name__  # Get the type of the data
        super().__init__(self._generate_message())

    def _generate_message(self):
        """Generate an error message."""
        return (
            f"Error occurred while parsing {self.data.__name__} which is data of type '{self.data_type}' "
            f"with function '{self.func_name}'. Data: {self.data}"
        )


class Parse:
    """Takes in a python dictionary and parses values"""

    key_function_mapping_dict = {
        "published_date": "parse_published_at",
        "published_at": "parse_published_at",
        "pub_date": "parse_published_at",
        "date": "parse_published_at",
        "photos": "parse_photos",
        "location": "parse_location_obj",
        "LOCATION": "parse_location_obj",
        "city": "parse_location_obj",
        "CITY": "parse_location_obj",
        "state": "parse_location_obj",
        "STATE": "parse_location_obj",
        "country": "parse_location_obj",
        "COUNTRY": "parse_location_obj",
        "description": "parse_description",
        "bio": "parse_description",
        "Description": "parse_description",
        "Bio": "parse_description",
        "DESCRIPTION": "parse_description",
        "BIO": "parse_description",
    }
    parsed = None  # parsed output
    parsed_keys = set()  # set of keys filtered
    success_flag = False

    def __init__(self, type=None):
        """Initialize the Parse object, taking in a dictionary and an optional type."""

        self.type = type
        self.parsed = None
        self.parsed_keys = set()
        self.success_flag = False

        self.parsed_types_tuples = self.get_parsed_types_types()

    @property
    def meta_data(self):
        """Return metadata associated with the parsed object."""
        return {
            "type": self.type,
            "parsed_keys": list(self.parsed_keys),
            "results": self.parsed,
            "success_flag": self.success_flag,
            "status": self.success_flag,
        }

    def _parse_format(parse_func, data):
        """
        Higher-order function that wraps a parsing function and handles errors.

        Args:
            parse_func (function): The parsing function to be wrapped.
            data (Any): The data to be passed into the parsing function.

        Returns:
            Any: Parsed data or the original data if an error occurs.

        Raises:
            ParsingError: If an exception occurs in the parsing function.
        """
        try:
            # Try parsing the data with the provided parsing function
            return parse_func(data)
        except Exception as e:
            # Log the error and raise a ParsingError with details
            print(f"Error in function '{parse_func.__name__}': {e}")
            raise ParsingError(data, parse_func.__name__) from e

    def parse(self, object=None):
        """Parse the input object, applying functions based on the key_function_mapping_dict."""
        if object is None:
            object = self.original_data
        elif not isinstance(object, dict):
            raise TypeError("Input must be a dictionary")

        parsed_object = {}
        for key, value in object.items():
            if key in self.key_function_mapping_dict:
                parsing_function = getattr(
                    self, self.key_function_mapping_dict[key], None
                )
                if parsing_function:
                    parsed_object[key] = parsing_function(value)
                    self.parsed_keys.add(key)
            else:
                parsed_object[key] = value  # Copy over keys that don't require parsing

        # Process 'published_at' if available
        if "published_at" in parsed_object:
            parsed_object["published_at"] = self.parse_published_at(
                parsed_object["published_at"], action="format"
            )
            parsed_object["date_delta"] = self.parse_published_at(
                parsed_object["published_at"], action="delta"
            )

        return parsed_object

    #############################################################################################################################################################################################
    # UTIL FUNCTIONS
    #############################################################################################################################################################################################

    def return_original(self):
        """Function to return original data object"""
        return self.original_data

    def get_parsed_types_types(self):
        """returns a set of tuples consisting of filtered attribute key (STR) and type of value parsed"""

        output = set()
        if len(self.parsed_keys) > 0:
            for key in self.parsed_keys:
                # add key & type of value being parsed
                output.add((key, type(self.original_data[key])))

        return output

    def clean_json(self, data):
        """
        Recursively clean JSON data
        """
        if isinstance(data, dict):
            return {k: self.clean_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.clean_json(item) for item in data]
        elif isinstance(data, str):
            return self.clean_text(data)
        else:
            return data

    def clean_text(self, text, *cleaning_rules):
        """
        Clean text by removing common artifacts
        """
        # Remove URL encoded characters (like %39)
        text = re.sub(r"%[0-9A-Fa-f]{2}", "", text)

        # Remove slashes in weird places
        text = re.sub(r"\[?/\'?(.+?)\'?/\]?", r"\1", text)

        # Remove extra whitespace
        text = " ".join(text.split())

        # Handle adding more cleaning rules as needed
        for formatting_func in cleaning_rules:
            additional_formatted_text = formatting_func(text)
            if (
                isinstance(additional_formatted_text, str)
                and len(additional_formatted_text.split("")) > 0
                and additional_formatted_text != ""
            ):
                text = additional_formatted_text
            else:
                print(
                    text,
                    "=> could not be further formatted by cleaning func",
                    formatting_func.__name__,
                )

        return text.strip()

    #############################################################################################################################################################################################
    # PARENT PARSING FUNCTIONS - Descriptions/Text block, Pub date, Photos, location
    #############################################################################################################################################################################################

    def parse_description(self, description):
        """
        Parse large blocks of text descriptions efficiently.
        Checks for JSON, loads if JSON data, and removes common artifacts.

        :param description: str, the description text to parse
        :return: dict or str, parsed description
        """
        if not description:
            return ""

        # Try to parse as JSON first
        try:
            parsed_json = json.loads(description)
            return self.clean_json(parsed_json)
        except json.JSONDecodeError:
            # If not JSON, process as plain text
            return self.clean_text(description)

    def parse_published_at(self, pub_date, action="any"):
        """Parse the published_date property in animal data object returned from API

        Args:
            pub_date (STRING): string date value returned from API
            action (STRING): the desired action to be done to the pub_date
                'delta' = get the difference between the pub_date and now() in days
                'format' = format the pub_date into a readable form
        """
        if action not in ["any", "delta", "format"]:
            raise TypeError("Wrong Action Type")

        if not pub_date:
            raise TypeError("truthy pub_date value is not provided")

        # Using current time with UTC timezone
        today = datetime.datetime.now(pytz.utc)
        parsed_date = None

        # Determine the input date format
        if "/" in pub_date:
            input_format = "%d/%m/%Y"
        elif "T" in pub_date:
            input_format = "%Y-%m-%dT%H:%M:%S%z"
        else:
            raise ValueError(f"Unsupported date format: {pub_date}")

        # Parse the date
        date_obj = datetime.datetime.strptime(pub_date, input_format)
        if action == "any":
            return {
                "published_at": self.parse_published_at(
                    pub_date=pub_date, action="format"
                ),
                "date_delta": self.parse_published_at(
                    pub_date=pub_date, action="delta"
                ),
            }
        # handle if action = 'delta'
        elif action == "delta":
            # If the parsed date doesn't have timezone info, assume it's UTC
            if date_obj.tzinfo is None:
                date_obj = date_obj.replace(tzinfo=pytz.utc)
            date_diff = today - date_obj
            # get the difference in days
            parsed_date = date_diff.days
            return parsed_date

        # handle if action = 'format'
        elif action == "format":
            parsed_date = date_obj.strftime("%d/%m/%Y")
            return parsed_date

    def parse_location_obj(self, loc_obj):
        """Function to parse location object property in API results"
        if not loc_obj or country:
                return None"""
        # grab city, state, country
        city = loc_obj.get("city", False)
        state = loc_obj.get("state", False)
        country = loc_obj.get("country", False)
        if country:
            # parse country string into 2 letter abbreviations
            country = (
                country
                if (len(country) == 2)
                else pycountry.countries.search_fuzzy(country)[0].alpha_2
            )
        if not loc_obj or not country:
            return ""
        elif city:  # if city, state, country
            # clean city, state, country strings

            if state:
                # parse state string into 2 letter abbreviations
                state = (
                    state
                    if (len(state) == 2)
                    else pycountry.subdivisions.search_fuzzy(state)[0].alpha_2
                )
                return {
                    "location": "%s,%s" % (city, state),
                    "state": state,
                    "country": country,
                    "city": city,
                }
        else:  # if state, country
            if state:
                return {
                    "location": "%s,%s" % (state, country),
                    "state": state,
                    "country": country,
                }
            else:  # if only country
                return {
                    "location": "%s" % (country),
                    "country": country,
                }

    def parse_photos(self, photos_list, type):
        """Function to parse breeds object property in API results"""

        # handle invalid or empty types
        if type.lower() not in [
            "dog",
            "cat",
            "horse",
            "bird",
            "rabbit",
            "small-furry",
            "barn-yard",
            "scales-fins-other",
        ]:
            type = "misc"

        # dictionary of urls for the graphics
        default_animal_graphic = {
            "dog": "../static/images/graphics/dog-freepik.png",
            "cat": "../static/images/graphics/cat-freepik.png",
            "horse": "../static/images/graphics/horse-freepik.png",
            "bird": "../static/images/graphics/bird-eucalyp.png",
            "small-furry": "../static/images/graphics/small-furry-freepik.png",
            "scales-fins-other": "../static/images/graphics/scales-smashicons.png",
            "barnyard": "../static/images/graphics/scales-smashicons.png",
            "rabbit": "../static/images/graphics/rabbit-freepik.png",
            "misc": "../static/images/graphics/tracks_freepik.png",
        }

        if not photos_list or len(photos_list) == 0:
            return default_animal_graphic[
                type.lower()
            ]  # return default graphic if the animal has no photos
        else:
            return photos_list[0]["full"]


class ParseAnimal(Parse):
    """
    Parser subclass to handle parsing singular animal data object
    """

    # Update the parent key_function_mapping_dict with animal-specific mappings
    key_function_mapping_dict = Parse.key_function_mapping_dict.copy().update(
        {
            # animal specific keys-funcs
            "breeds": "parse_breeds",
            "breed": "parse_breeds",
            "BREED": "parse_breeds",
            "BREEDs": "parse_breeds",
            "color": "parse_color",
            "colour": "parse_color",
            "COLOUR": "parse_color",
            "colours": "parse_color",
            "COLOURS": "parse_color",
            "COLOR": "parse_color",
            "colors": "parse_color",
            "COLORS": "parse_color",
        }
    )
    type = "animal"

    #############################################################################################################################################################################################
    # UTILITY FUNCTIONS
    #############################################################################################################################################################################################

    def check_for_nested(self, data={}):
        """
        Helper function to check if data is nested and needs to be deserialized prior to parsing.

        Args:
            data (Any): value to be checked for nesting

        Returns:
            dict: Representing a SINGLE Animal

        Raises:
            ValueError: If empty data or multiple objects are passed
            TypeError: If the data format is incorrect
        """
        if not data:
            raise ValueError("Empty data passed for parsing")

        # Keys that can indicate multiple objects or a nested structure
        multi_obj_keys = ("animals", "organizations", "orgs")
        single_obj_keys = tuple(key[:-1] for key in multi_obj_keys)  # Singular forms

        # If the data is already in dict format, check if it's a valid animal object
        if isinstance(data, dict):
            # Check for nested multi-object structure like {'animals': [<animal1>, <animal2>]}
            for key in multi_obj_keys:
                if key in data and isinstance(data[key], list):
                    if len(data[key]) == 1:  # If it's a list with one animal
                        # Recursively check the nested structure
                        return self.check_for_nested(data[key][0])
                    elif len(data[key]) > 1:
                        raise ValueError(f"Multiple objects found in '{key}' key")

            # Check for nested single-object structure like {'animal': {...}}
            for key in single_obj_keys:
                if key in data and isinstance(data[key], dict):
                    # Return the single animal object
                    return data[key]

            # If already a valid animal object with common keys, return it
            common_animal_keys = [
                "id",
                "type",
                "organization_id",
                "breed",
                "color",
                self.key_function_mapping_dict.keys(),
            ]
            if any(key.lower() in common_animal_keys for key in data.keys()):
                return data  # Return if it has common animal object keys

        elif isinstance(data, list):
            # If it's a list with one animal, process it recursively
            if len(data) == 1:
                return self.check_for_nested(data[0])
            else:
                raise ValueError(
                    "Multiple objects passed in a list for a single animal"
                )

        # If no valid format is found
        raise ValueError(f"Unexpected data structure: {type(data)} {data}")

    #############################################################################################################################################################################################
    # PARSING FUNCTIONS
    #############################################################################################################################################################################################
    def parse(self, data={}):
        """Dynamically parses the animal data."""
        if not data or not isinstance(data, dict):
            raise TypeError("Animal data must be a non-empty dictionary.")

        for key, value in data.items():
            func_name = self.key_function_mapping_dict.get(key.lower(), None)
            if func_name:
                parse_func = getattr(self, func_name)
                print(parse_func)
                if callable(parse_func):
                    try:
                        # Use _parse_format to handle parsing and errors
                        self.results[key] = super()._parse_format(parse_func, value)
                    except ParsingError as e:
                        # Return original key/value if a ParsingError is raised
                        print(f"ParseAnimal.parse() error @: {key}:{value} {e}")
                        self.results[key] = value
                else:
                    self.results[key] = value
            else:
                self.results[key] = value

    def get_results(self):
        """Return the parsed results."""
        return self.results

    def parse_color(self, colors_obj):
        """Parse the colors object in an animal data object returned from API to remove false or null values"""
        print(colors_obj)
        if not colors_obj or not colors_obj["primary"]:
            return "Unknown Color"  # color is Unknown Color by default

        primary = colors_obj["primary"] or ""
        secondary = colors_obj["secondary"] or False
        tertiary = colors_obj["tertiary"] or False

        if tertiary:
            if secondary:
                print("parse colors output", f"{primary}/ {secondary}")
                return f"{primary}/ {secondary}"
            else:
                print("parse colors output", primary)
                return f"{primary}"
        else:
            print("parse colors output", primary)
            print("parse colors output")
            return primary

    def parse_breed(self, breeds_obj):
        """Function to parse breeds object property in a single Animal result from PetFinder API results"""
        if isinstance(breeds_obj, str):
            # return breeds_obj if it's already a string
            return breeds_obj
        if not breeds_obj or breeds_obj["unknown"] == True:
            return "Mystery Mix"  # breed is Mystery Mix by default
        elif isinstance(breeds_obj, str):
            return breeds_obj
        elif isinstance(breeds_obj, dict):
            primary = breeds_obj["primary"] or ""
            secondary = breeds_obj["secondary"] or False
            mixed_bool = breeds_obj["mixed"] or False
            unknown_bool = breeds_obj["unknown"] or False
            # check if unknown breed
            if unknown_bool == True:
                return "Mystery Mix"
            # check if mixed breed
            if mixed_bool == True:
                # check if secondary breed is provided
                if secondary:
                    return f"{primary} {secondary} mix"
                else:
                    return f"{primary} Mix"
            else:
                return primary
        else:
            print("parsing breeds error on => ", breeds_obj)
            return "Mystery Mix"  # breed is Mystery Mix by default


def parse_multi_animal(animal_list):
    """
    Function to parse multiple animal objects.
    Returns original object if any error occurs during parsing.
    """
    parsed_animals = []

    # Ensure the input is a non-empty iterable
    if animal_list and isinstance(animal_list, Iterable) and len(animal_list) > 0:
        for idx, animal in enumerate(animal_list):
            try:
                # Ensure animal is a dictionary before parsing
                if not isinstance(animal, dict):
                    raise TypeError(f"Animal at index {idx} is not a dictionary")
                
                # Parse the individual animal
                parser = ParseAnimal()
                animal_result = parser.parse(data=animal)
                parsed_animals.append(animal_result)
            except ParsingError as e:
                # Handle ParsingError, reset original data in the animal object
                print(f"ParsingError at index {idx}: {e}; Continuing with the rest")
                animal[e.data_key] = e.data  # Restore the original key-value
                parsed_animals.append(animal)
            except Exception as e:
                animal_name = (
                    animal["name"] if animal["name"] else f"{animal['type']}#{idx}"
                )
                # Log any other unexpected exceptions and skip the current animal
                print(
                    f"Unexpected error parsing animal {animal_name} at index {idx}: {e}; Skipping"
                )
                parsed_animals.append(animal)  # Add original animal if unexpected error

    return parsed_animals
