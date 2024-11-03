"""
Parser class to parse API results
"""

import datetime
import pytz
import pycountry
import json
import re
import json
import html
from copy import deepcopy
from collections.abc import Iterable
from flask import url_for
import traceback
from difflib import get_close_matches
import os


class ParsingError(Exception):
    """The ParsingError class will store the details of the error, including the original data, its type, and the parsing function that failed.

    Args:
        data (any): original data that needed to be parsed
        func_name (string): parsing function that failed
    """

    def __init__(self, data, func_name):
        self.data = data
        self.data_key = (
            data.__name__ if data.__name__ else data
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
        "status_changed_at": "parse_published_at",
        "published_date": "parse_published_at",
        "published_at": "parse_published_at",
        "pub_date": "parse_published_at",
        "date": "parse_published_at",
        "photos": "parse_photos",
        "primary_photo_cropped": "parse_photos",
        "PRIMARY_PHOTO_CROPPED": "parse_photos",
        "photo": "parse_photos",
        "PHOTO": "parse_photos",
        "PHOTOS": "parse_photos",
        "location": "parse_address",
        "LOCATION": "parse_address",
        "city": "parse_address",
        "CITY": "parse_address",
        "state": "parse_address",
        "STATE": "parse_address",
        "country": "parse_address",
        "COUNTRY": "parse_address",
        "description": "parse_description",
        "bio": "parse_description",
        "Description": "parse_description",
        "Bio": "parse_description",
        "DESCRIPTION": "parse_description",
        "BIO": "parse_description",
        "name": "parse_scription",
        "type":"prettify_animal_type",
    }
    parsed = None  # parsed output
    parsed_keys = set()  # set of keys filtered
    success_flag = False

    
    # def __init__(self, type=None):
    #     """Initialize the Parse object, taking in a dictionary and an optional type."""

    #     self.type = type
    #     self.parsed = None
    #     self.parsed_keys = set()
    #     self.success_flag = False

    # self.parsed_types_tuples = self.get_parsed_types_types()
    # Define mapping as a class attribute
    
    PRETTIFIED_MAPPING = {
        "dog": "Dog",
        "cat": "Cat",
        "rabbit": "Rabbit",
        "small-furry": "Small & Furry",
        "horse": "Horse",
        "bird": "Bird",
        "scales-fins-other": "Scales, Fins & Other",
        "barnyard": "Barnyard"
    }

    @classmethod
    def get_default_prettified_animal_types(cls):
        """Return the list of default prettified animal types."""
        
        api_type_key = "API_ANIMAL_TYPES"
        default_prettified_animal_types = cls.PRETTIFIED_MAPPING.values()
        
        if api_type_key in os.environ:
            types_list = json.loads(os.environ.get(api_type_key))
            return list(types_list or default_prettified_animal_types)
        
        #return default
        return list(default_prettified_animal_types)

    @property
    def meta_data(self):
        """Return metadata associated with the parsed object, eg. for debugging
        """
        return {
            "type": self.type,
            "parsed_keys": list(self.parsed_keys),
            "results": self.parsed,
            "success_flag": self.success_flag,
            "status": self.success_flag,
        }

    def _parse_format(self, parse_func, data):
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
        except ParsingError as pe:
            print(f"Error in function '{parse_func.__name__}': {pe}")
            # return original data
            return data

    def parse(self, object=None):
        """Parse the input object, applying functions based on the key_function_mapping_dict."""
        if object is None:
            object = {}
        elif not isinstance(object, dict):
            raise TypeError("Input must be a dictionary")

        parsed_object = {}
        for key, value in object.items():
            if key in self.key_function_mapping_dict:
                parsing_function = getattr(
                    self, self.key_function_mapping_dict[key], None
                )
                if parsing_function:
                    print(parsing_function, f"PARSING => {key}:", value)
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
    @classmethod
    def prettify_animal_types(cls, animal_types, fuzzy_match=True):
        """
        Convert a list of lowercase, hyphenated animal type strings to prettified names.

        Args:
            animal_types (list): List of lowercase, hyphenated animal type names.
            fuzzy_match (bool): Whether to use fuzzy matching if exact match not found.

        Returns:
            list: List of prettified animal type names in the same order as input.
        """
        prettified_types = []
        if isinstance(animal_types, (list, set, tuple)):
            for animal_type in animal_types:
                # Try exact match first
                prettified = cls.PRETTIFIED_MAPPING.get(animal_type.lower())
                
                if prettified is None and fuzzy_match:
                    # If no exact match and fuzzy matching is enabled, try fuzzy matching
                    close_matches = get_close_matches(animal_type.lower(), cls.get_default_prettified_animal_types(), n=1, cutoff=0.6)
                    if close_matches:
                        prettified = cls.PRETTIFIED_MAPPING[close_matches[0]]

                prettified_types.append(prettified if prettified else animal_type.capitalize())
            
            #return the first value if prettified types == 1
            return str(prettified_types[0]) if len(prettified_types) == 1 else prettified_types
        elif isinstance(animal_types, str):
            prettified = cls.PRETTIFIED_MAPPING.get(animal_types.lower())
            if prettified is None and fuzzy_match:
                close_matches = get_close_matches(animal_type.lower(), cls.get_default_prettified_animal_types(), n=1, cutoff=0.6)
                if close_matches:
                    prettified = close_matches[0] if close_matches[0] == cls.PRETTIFIED_MAPPING.get(animal_types.lower()) else cls.PRETTIFIED_MAPPING.get(animal_types.lower())
            
            return prettified or animal_types.capitalize()
        else:
            raise TypeError(f"Wrong type passed in for 'animal_types' param, expected str or iterable, got: type({animal_types}) = {type(animal_types)}")
        
    def return_original(self):
        """Function to return original data object"""
        return self.original_data

    def get_parsed_types_types(self, data, parsed_key_list):
        """returns a set of tuples consisting of filtered attribute key (STR) and type of value parsed"""

        output = set()
        if len(parsed_key_list) > 0:
            for key in parsed_key_list:
                # add key & type of value being parsed
                output.add((key, type(data[key])))

        return output

    #############################################################################################################################################################################################
    # PARENT PARSING FUNCTIONS - Descriptions/Text block, Pub date, Photos, location
    #############################################################################################################################################################################################

    def normalize_name(self, name_str: str) -> str:
        """
        Helper function that takes a string of a name (which can be a series of words) and returns the string with the first letter of each word capitalized and the rest in lowercase:

        example useage:
        print(format_name("SUNNY SPARKY"))  # Output: Sunny Sparky
        print(format_name("wonder PUP"))    # Output: Wonder Pup
        print(format_name("jOHN dOE"))      # Output: John Doe
        print(format_name("MARY JANE WATSON"))  # Output: Mary Jane Watson
        """

        # Split the name into words
        words = name_str.split()
        filler_words = [
            "hold",
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "up",
            "about",
            "into",
            "over",
            "after",
            "beneath",
            "under",
            "above",
            "that",
            "which",
            "who",
            "whom",
            "whose",
            "however",
            "therefore",
            "thus",
            "hence",
            "consequently",
            "nevertheless",
            "moreover",
            "furthermore",
            "additionally",
            "indeed",
            "arguably",
            "certainly",
            "clearly",
            "obviously",
            "perhaps",
            "maybe",
            "possibly",
            "probably",
            "likely",
            "seemingly",
            "apparently",
            "evidently",
            "notably",
            "significantly",
            "especially",
            "particularly",
            "specifically",
            "generally",
            "usually",
            "typically",
            "often",
            "sometimes",
            "occasionally",
            "rarely",
            "seldom",
            "never",
            "always",
            "frequently",
            "subsequently",
            "previously",
            "formerly",
            "latterly",
            "recently",
            "currently",
            "presently",
            "immediately",
            "instantly",
            "directly",
            "indirectly",
            "ultimately",
            "eventually",
            "finally",
            "lastly",
            "in conclusion",
            "to summarize",
            "in summary",
            "altogether",
            "overall",
            "generally speaking",
            "broadly speaking",
            "in essence",
            "in effect",
            "as a result",
            "consequently",
            "as such",
            "accordingly",
            "hence",
        ]

        # Capitalize the first letter of each word and make the rest lowercase
        formatted_words = [
            word.capitalize() if word not in filler_words else word.lower()
            for word in words
        ]

        # Join the words back together
        return " ".join(formatted_words)

    def parse_description(self, description):
        """
        Parse large blocks of text descriptions efficiently.
        Checks for JSON, loads if JSON data, and removes common artifacts.

        :param description: str, the description text to parse
        :return: dict or str, parsed description
        """
        if not description or not isinstance(description, str):
            return description

        # Try to parse as JSON first
        try:
            parsed_json = json.loads(description)
            return self.clean_json(parsed_json)
        except json.JSONDecodeError:
            # If not JSON, process as plain text
            return self.clean_text(description)

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

    def format_kebob_case(input_string) -> str: 
        """Helper function to remove underscores & capitalize input string text  

        Args:
            input_string (str): string text to remove underscores & capitalize

        Returns:
            str: formatted string text 
        """
        # Guard clause: return the original string if no underscores are found
        if '_' not in input_string:
            return input_string
        
        # Split the string by underscores, capitalize each part, and join them back with spaces
        return ' '.join(part.capitalize() for part in input_string.split('_'))
    
    def clean_text(self, text, *cleaning_rules) -> str:
        """
        Clean text by removing common artifacts, unescaping HTML, and applying other cleaning rules.

        :param text: str, the text to clean
        :param cleaning_rules: additional cleaning functions to apply
        :return: str, the cleaned text
        """
        if not cleaning_rules:
            cleaning_rules = self.format_kebob_case(input_string=text)
        # Unescape any HTML entities (e.g., &quot;, &amp;, etc.)
        text = html.unescape(text)

        # Remove URL encoded characters (like %39)
        text = re.sub(r"%[0-9A-Fa-f]{2}", "", text)

        # Remove slashes in weird places (e.g., \'text\' becomes 'text')
        text = re.sub(r"\[?/\'?(.+?)\'?/\]?", r"\1", text)

        # Remove extra whitespace (including newline characters like \n)
        text = " ".join(text.split())

        # Apply any additional cleaning rules provided
        for formatting_func in cleaning_rules:
            additional_formatted_text = formatting_func(text)
            if (
                isinstance(additional_formatted_text, str)
                and additional_formatted_text.strip() != ""
            ):
                text = additional_formatted_text
            else:
                print(
                    f"{text} => could not be further formatted by cleaning func {formatting_func.__name__}"
                )

        return text.strip()

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

    def parse_address(self, loc_obj):
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
            return "Unknown Location"
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
        """Function to parse the photos property in API results."""
        default_photo_folder_name = "images/graphics"

        # Handle invalid or empty types
        if not type or type.lower() not in [
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
            misc_photo_name = "tracks_freepik.png"
            return url_for(
                "static",
                filename=f"{default_photo_folder_name}/{misc_photo_name}",
                _external=True,
            )

        # Dictionary of URLs for the graphics
        default_animal_graphic = {
            "dog": "dog-freepik.png",
            "cat": "cat-freepik.png",
            "horse": "horse-freepik.png",
            "bird": "bird-eucalyp.png",
            "small-furry": "small-furry-freepik.png",
            "scales-fins-other": "scales-smashicons.png",
            "barnyard": "scales-smashicons.png",
            "rabbit": "rabbit-freepik.png",
            "misc": "tracks_freepik.png",
        }

        # If no photos are available or the list is empty
        if not photos_list:
            default_filename = default_animal_graphic.get(
                type.lower(), default_animal_graphic["misc"]
            )
            return url_for(
                "static",
                filename=f"{default_photo_folder_name}/{default_filename}",
                _external=True,
            )

        # If the photos_list is a string (a direct URL)
        if isinstance(photos_list, str):
            return photos_list  # Return the string directly

        # Otherwise, return the first photo URL in the list
        if isinstance(photos_list, list) and "full" in photos_list[0]:
            return photos_list[0]["full"]

        # Fallback for any other case
        final_url = url_for(
            "static",
            filename=f"{default_photo_folder_name}/{default_animal_graphic['misc']}",
            _external=True,
        )
        if not photos_list:
            print("No photos received, default image URL =", final_url)
        return final_url


class ParseAnimal(Parse):
    """
    Parser subclass to handle parsing a singular animal data object.
    """

    def __init__(self, animal_data):
        """
        Initialize ParseAnimal with an animal data object.
        """
        self.data = animal_data
        self.parsed_keys = set()
        self.results = {}

    # Update the key_function_mapping_dict with animal-specific mappings
    key_function_mapping_dict = Parse.key_function_mapping_dict.copy()
    key_function_mapping_dict.update(
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
                        # return self.check_for_nested(data[key][0])
                        return data[key][0]
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
    def parse(self):
        """
        Parse the animal data using the key_function_mapping_dict.
        """
        if isinstance(self.data, dict):
            for key, value in self.data.items():
                if key.lower() in ("name", "names"):
                    self.results[key] = self.clean_text(value, self.normalize_name)
                elif key.lower() in ("breed", "breeds"):
                    # parse breeds and set object
                    self.results[key] = (
                        self.parse_breed(value) if isinstance(value, dict) else value
                    )
                    self.parsed_keys.add(key)
                # parse animal photos
                elif key.lower() in ("photo", "photos", "media"):
                    # Handle parse_photos which requires multiple arguments
                    self.results[key] = self.parse_photos(
                        photos_list=value,
                        # grab "type" or "species" of data
                        type=self.data.get("type", self.data.get("species", "misc")),
                    )
                    self.parsed_keys.add(key)
                # parse animal address
                elif key.lower() in (
                    "location",
                    "locations",
                    "city",
                    "address",
                    "state",
                    "country",
                    "locale",
                    "contact",
                ):
                    # TODO: need to fix this as accessing animal.location is easier plus it doesn't handle non-dict situations cleanly
                    # handle if key = "contact" and the address DICT is nested within
                    if key == "contact":
                        location = value["address"] if "address" in value else value
                        self.results["location"] = (
                            self.parse_address(location)
                            if isinstance(location, dict)
                            else (
                                self.clean_text(location, self.normalize_name)
                                if isinstance(location, str)
                                else "Unknown Location"
                            )
                        )
                    else:
                        self.results[key] = (
                            self.parse_address(value)
                            if isinstance(value, dict)
                            else (
                                self.clean_text(value, self.normalize_name)
                                if isinstance(value, str)
                                else "Unknown Location"
                            )
                        )
                    self.parsed_keys.add(key)

                elif key.lower() in ("bio", "description", "biography", "story"):
                    self.results[key] = self.parse_description(value)
                    self.parsed_keys.add(key)

                elif key.lower() in (
                    "color",
                    "colors",
                    "colour",
                    "colours",
                    "coat color",
                ):
                    self.results[key] = self.parse_color(value)
                    self.parsed_keys.add(key)
                elif key.lower() in (
                    "coat",
                    "coats",
                ):
                    self.results[key] = value if value else "Mystery Coat"
                    self.parsed_keys.add(key)
                elif key.lower() in (
                    "published_at",
                    "published",
                    "date",
                    "publish-date",
                    "pub_date",
                    "date",
                ):
                    parsed_date_obj = self.parse_published_at(
                        pub_date=value, action="any"
                    )
                    self.results["published_at"] = parsed_date_obj["published_at"]
                    self.results["date_delta"] = parsed_date_obj["date_delta"]
                    self.parsed_keys.add(key)
                else:
                    self.results[key] = value
                    self.parsed_keys.add(key)

        print(
            self.data.get("name", "unknown animal"), "keys parsed =", self.parsed_keys
        )
        return self.results

    def parse_color(self, colors_obj):
        """Parse the colors object in an animal data object returned from API to remove false or null values"""
        if not colors_obj:
            return "Unknown Color"  # color is Unknown Color by default
        if isinstance(colors_obj, str):
            return self.normalize_name(
                colors_obj
            )  # return cleaned str if already a str

        primary = colors_obj["primary"] or "Unknown Color"
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
            return (
                primary
                if primary and primary not in ["", "_", "__", None]
                else "Unknown Color"
            )

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
    parsed_id = set()

    # Ensure the input is a non-empty iterable
    if animal_list and isinstance(animal_list, Iterable) and len(animal_list) > 0:
        for idx, animal in enumerate(animal_list):
            try:
                # Ensure animal is a dictionary before parsing
                if not isinstance(animal, dict):
                    raise TypeError(
                        f"Animal at index {idx} is not a dictionary. Animal = {animal}"
                    )

                # Parse the individual animal
                parser = ParseAnimal(animal_data=animal)
                animal_result = parser.parse()
                if "name" not in parsed_id:
                    parsed_id.add(animal_result.get("name"))
                    parsed_animals.append(animal_result)

            except ParsingError as e:
                # Handle ParsingError, reset original data in the animal object
                print(f"ParsingError at index {idx}: {e}; Continuing with the rest")
                animal[e.data_key] = e.data  # Restore the original key-value
                parsed_id.add(animal["name"])
                if animal["name"] in parsed_id:
                    parsed_animals.append(animal)

            except TypeError as e:
                # Handle TypeError specifically

                print(idx, "=", animal["name"])
                # Get the full traceback as a string
                error_traceback = traceback.format_exc()

                # Print the error message
                print(f"TypeError occurred: {str(e)}")

                # Print the full traceback
                print("Full traceback:")
                print(error_traceback)

                # Get the most recent call last (where the error occurred)
                tb = traceback.extract_tb(e.__traceback__)
                filename, line_number, func_name, text = tb[-1]
                print(
                    f"Error occurred in file {filename}, line {line_number}, in {func_name}"
                )
                print(f"The erroneous line of code: {text}")

                print(f"TypeError at index {idx}: {e}; Skipping animal.")
                parsed_id.add(animal["name"])
                if animal["name"] in parsed_id:
                    parsed_animals.append(animal)

            except KeyError as e:
                print(idx, "=", animal["name"])
                # Get the full traceback as a string
                error_traceback = traceback.format_exc()

                # Print the error message
                print(f"TypeError occurred: {str(e)}")

                # Print the full traceback
                print("Full traceback:")
                print(error_traceback)

                # Get the most recent call last (where the error occurred)
                tb = traceback.extract_tb(e.__traceback__)
                filename, line_number, func_name, text = tb[-1]
                print(
                    f"Error occurred in file {filename}, line {line_number}, in {func_name}"
                )
                print(f"The erroneous line of code: {text}")

                # Handle KeyError specifically
                print(f"KeyError at index {idx}: Missing key {e}; Skipping animal.")
                parsed_id.add(animal["name"])
                if animal["name"] in parsed_id:
                    parsed_animals.append(animal)

            except AttributeError as e:
                print(idx, "=", animal["name"])
                # Get the full traceback as a string
                error_traceback = traceback.format_exc()

                # Print the error message
                print(f"TypeError occurred: {str(e)}")

                # Print the full traceback
                print("Full traceback:")
                print(error_traceback)

                # Get the most recent call last (where the error occurred)
                tb = traceback.extract_tb(e.__traceback__)
                filename, line_number, func_name, text = tb[-1]
                print(
                    f"Error occurred in file {filename}, line {line_number}, in {func_name}"
                )
                print(f"The erroneous line of code: {text}")

                # Handle AttributeError specifically
                print(f"AttributeError at index {idx}: {e}; Skipping animal.")
                parsed_id.add(animal.get("name"))
                if animal.get("name") in parsed_id:
                    parsed_animals.append(animal)

            except Exception as e:
                print(idx, "=", animal["name"])
                # Get the full traceback as a string
                error_traceback = traceback.format_exc()

                # Print the error message
                print(f"TypeError occurred: {str(e)}")

                # Print the full traceback
                print("Full traceback:")
                print(error_traceback)

                # Get the most recent call last (where the error occurred)
                tb = traceback.extract_tb(e.__traceback__)
                filename, line_number, func_name, text = tb[-1]
                print(
                    f"Error occurred in file {filename}, line {line_number}, in {func_name}"
                )
                print(f"The erroneous line of code: {text}")

                # Handle any other unexpected exceptions
                animal_name = animal.get(
                    "name", f"{animal.get('type', 'Animal')}#{idx}"
                )
                print(
                    f"Unexpected error parsing animal {animal_name} at index {idx}: {e}; Skipping"
                )
                parsed_id.add(animal["name"])
                if animal["name"] in parsed_id:
                    parsed_animals.append(
                        animal
                    )  # Add original animal if unexpected error
    print(parsed_id)
    return parsed_animals
