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


class Parse:
    """Takes in a python dictionary and parses values"""

    key_function_mapping_dict = {
        "published_date": "parse_publish_date",
        "pub_date": "parse_publish_date",
        "date": "parse_publish_date",
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

    def __init__(self, object={}, type=None):
        self.original_data = deepcopy(object)
        self.type = type
        self.success_flag = False
        self.parsed_types_tuples = self.get_parsed_types_types()

        try:
            self.parsed = self.parse(object=object)
            # check for success
            self.success_flag = (
                True
                if self.parsed and len(self.meta_data["parsed_keys"]) > 0
                else False
            )
            if not self.success_flag:
                raise ValueError(f"Failed parsing from {object}")
                # error handle as necessary
            return self.meta_data["results"]
        except ValueError as v_e:
            print(f"Parsing Value error {v_e} {self.meta_data}")
            self.success_flag = False
            return self.original_data
        except TypeError as t_e:
            print(f"Parsing Input error {t_e} {self.meta_data}")
            self.success_flag = False
            return self.original_data
        except Exception as e:
            print(f"Parsing (general) error {e} {self.meta_data}")
            self.success_flag = False
            return self.original_data

    @property
    def meta_data(self):
        """
        The `meta_data` function returns a dictionary containing various metadata related to the object.
        :return: A dictionary is being returned with the following keys and values:
        - "type": the value of the `type` attribute of the object
        - "parsed_keys": the value of the `parsed_types_tuples` attribute of the object
        - "results": the value of the `parsed` attribute of the object
        - "success_flag": the value of the `success_flag` attribute of the object
        """
        return {
            "type": self.type,
            "parsed_keys": list(self.parsed_types_tuples),
            "results": self.parsed,
            "success_flag": self.success_flag,
            "status": self.success_flag,
        }

    def parse(self, object=None):
        """
        Parse the input object or the original data stored in the instance.

        Args:
            object (dict, optional): Python dictionary of data to be parsed.
                If None, uses the original_data stored in the instance.

        Returns:
            dict: A new dictionary containing the parsed data.

        Raises:
            ValueError: If no data is available to parse.
        """
        if object is None:
            if not self.original_data:
                raise ValueError("No data to parse")
            object = self.original_data
        elif not self.original_data:
            self.original_data = deepcopy(object)

        if not isinstance(object, dict):
            raise TypeError("Input must be a dictionary")

        parsed_object = {}
        for key, value in object.items():
            if key in self.key_function_mapping_dict:
                parsing_function = getattr(self, self.key_function_mapping_dict[key])
                parsed_object[key] = parsing_function(value)
                self.parsed_keys.add(key)
            else:
                # Copy over keys that don't need parsing
                parsed_object[key] = value

        # Additional processing for dates (moved from Approach 2)
        if "published_at" in parsed_object:
            parsed_object["published_at"] = self.parse_publish_date(
                parsed_object["published_at"], action="format"
            )

            parsed_object["date_delta"] = self.parse_publish_date(
                parsed_object["published_at"], action="delta"
            )
        print(
            f"Parsed obj={self.meta_data.type if self.meta_data.type else self.__name__}, keys parsed={self.parsed_keys}"
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

    def parse_publish_date(self, pub_date, action="delta"):
        """Parse the published_date property in animal data object returned from API

        Args:
            pub_date (STRING): string date value returned from API
            action (STRING): the desired action to be done to the pub_date
                'delta' = get the difference between the pub_date and now() in days
                'format' = format the pub_date into a readable form
        """
        if action not in ["delta", "format"]:
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

        # handle if action = 'delta'
        if action == "delta":
            # If the parsed date doesn't have timezone info, assume it's UTC
            if date_obj.tzinfo is None:
                date_obj = date_obj.replace(tzinfo=pytz.utc)
            date_diff = today - date_obj
            # get the difference in days
            parsed_date = date_diff.days
            return parsed_date

        # handle if action = 'format'
        if action == "format":
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
            return None
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

    # Update the parent key_function_mapping_dict with animal specific mappings
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

    def __init__(self, object):
        preparsed_object = self.check_for_nested(object)
        super().__init__(object=preparsed_object)
        return self.meta_data["results"]

    #############################################################################################################################################################################################
    # UTILITY FUNCTIONS
    #############################################################################################################################################################################################

    def check_for_nested(self, data):
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
        multi_obj_keys = ("animals", "organizations", "orgs")
        single_obj_keys = tuple(
            key[:-1] for key in multi_obj_keys
        )  # Remove last character to make singular

        if isinstance(data, dict):
            # Check for nested multi-object structure
            for key in multi_obj_keys:
                if key in data and isinstance(data[key], list):
                    if len(data[key]) == 1:
                        return self.check_for_nested(data[key][0])
                    elif len(data[key]) > 1:
                        raise ValueError(f"Multiple objects found in '{key}' key")

            # Check for nested single-object structure
            for key in single_obj_keys:
                if key in data:
                    return self.check_for_nested(data[key])

            # Check if it's already the desired format
            if any(
                key.lower() in self.key_function_mapping_dict for key in data.keys()
            ):
                return data

        elif isinstance(data, (list, tuple, set)):
            if not data:
                raise ValueError("Empty data passed in for parsing")
            elif len(data) == 1:
                return self.check_for_nested(data[0])
            else:
                raise ValueError(f"Multiple objects passed in for processing: {data}")

        else:
            raise TypeError(f"Incorrect data format: {type(data)}")

        # If we've reached here, the structure is unexpected
        raise ValueError(f"Unexpected data structure: {data}")

    #############################################################################################################################################################################################
    # PARSING FUNCTIONS
    #############################################################################################################################################################################################

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


class ParseMultiAnimal(ParseAnimal):
    """
    Parses multiple animal data objects
    """

    def __init__(self, iterable_animals):
        super().__init__(object={})  # Initialize parent with empty dict
        self.parsed = []
        self.success_flag = False

        if not iterable_animals:
            raise ValueError(f"Nothing passed for parsing @ {self.__class__.__name__}")
        if not isinstance(iterable_animals, Iterable):
            raise TypeError(f"Non-iterable type passed in: {type(iterable_animals)}")

        self._parse_animals(iterable_animals)

    def _parse_animals(self, iterable_animals):
        for idx, animal in enumerate(iterable_animals):
            try:
                parsed_animal = ParseAnimal(animal).parse()
                self.parsed.append(parsed_animal)
                parsed_animal_identifier = parsed_animal.get("id", f"idx{idx}")
                self.parsed_keys.append(parsed_animal_identifier)
            except Exception as e:
                print(f"Error parsing animal at index {idx}: {e}")

        if self.parsed:
            self.success_flag = True

    @property
    def meta_data(self):
        """
        The `meta_data` function returns a dictionary containing metadata about a multi-animal parsing
        operation.
        :return: The `meta_data` property is returning a dictionary with the following keys and values:
        - "type": STR subject matter being interated
        - "parsed_keys": a list of keys from `self.parsed_keys`
        - "results": the parsed data from `self.parsed`
        - "success_flag": the success flag value from the object
        - "status": the success flag value from the object
        """
        return {
            "type": "multi_animal",
            "parsed_keys": list(self.parsed_keys),
            "results": self.parsed,
            "success_flag": self.success_flag,
            "status": self.success_flag,
        }
