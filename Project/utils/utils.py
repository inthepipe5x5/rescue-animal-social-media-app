from typing import Any, Dict, List, Optional, Union
from marshmallow_sqlalchemy.fields import String
from fuzzywuzzy import fuzz


# Custom Validator
class TwoCharString(String):
    def _deserialize(self, value, attr, data, **kwargs):
        if len(value) != 2:
            raise ValueError("Must be a 2-character string")
        return value


def fuzzy_match_str(val1: Any, val2: Any, match_threshold: int = 90) -> bool:
    """
    The `fuzzy_match` function compares two values, either strings using fuzzy matching with a specified
    threshold or other types directly for equality.

    :param val1: `val1` is the first value that will be compared in the `fuzzy_match` function. It can
    be of any data type, but if it's a string, the function will use fuzzy matching to compare it with
    `val2`
    :type val1: Any
    :param val2: val2 is the second value that will be compared in the fuzzy_match function. It can be
    of any data type, but if both val1 and val2 are strings, the function will use the fuzz.ratio method
    from the fuzzywuzzy library to calculate the similarity ratio between the two strings
    :type val2: Any
    :param match_threshold: The `match_threshold` parameter in the `fuzzy_match` function is an optional
    integer parameter that specifies the minimum threshold for the fuzzy matching ratio to consider two
    strings as a match. By default, the `match_threshold` is set to 90, meaning that if the fuzzy
    matching ratio between two, defaults to 90
    :type match_threshold: int (optional)
    :return: The `fuzzy_match` function returns `True` if the similarity ratio between `val1` and `val2`
    is greater than or equal to the `match_threshold` specified (default is 90) when both `val1` and
    `val2` are strings. Otherwise, it returns `True` if `val1` is equal to `val2`.
    """
    if isinstance(val1, str) and isinstance(val2, str):
        return fuzz.ratio(val1, val2) >= match_threshold
    return val1 == val2


def uppercase_2_chars(value):
    """
    Helper form filter function to always output 2 upper case str characters
    Intended to be used for state input fields
    """
    if value:
        value = value.upper()[:2]
    return value


def get_nested_value(data: Union[Dict, List], target_key: str, nesting_keys: Optional[List[str]] = None) -> Any:
    """
    Recursively traverse a complex data structure to retrieve a nested value.

    Args:
        data (Union[Dict, List]): The complex data structure to traverse.
        target_key (str): The key of the desired value to search for.
        nesting_keys (Optional[List[str]]): A list of keys to navigate through the structure.

    Returns:
        Any: The value found at the specified location or None if not found.
    """
    if not isinstance(data, (dict, list)):
        return None

    if nesting_keys:
        key = nesting_keys[0]
        if isinstance(data, dict):
            for data_key, value in data.items():
                if fuzzy_match_str(key, data_key):
                    if fuzzy_match_str(target_key, data_key):
                        return value
                    return get_nested_value(value, target_key, nesting_keys[1:])
        elif isinstance(data, list) and key.isdigit() and int(key) < len(data):
            return get_nested_value(data[int(key)], target_key, nesting_keys[1:])
        return None

    if isinstance(data, dict):
        for key, value in data.items():
            if fuzzy_match_str(target_key, key):
                return value
            result = get_nested_value(value, target_key)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = get_nested_value(item, target_key)
            if result is not None:
                return result

    return None
