from typing import TypeAlias, TypedDict, Optional, Union, List, Tuple
import datetime
from enum import Enum
from core import TwoCharString

class GeoLocation(TypedDict):
    latitude: float
    longitude: float

# This Union type allows for both dictionary and string representations of geolocation
GeoLocationType = Union[GeoLocation, str]  # str for "lat,lon" format

class UserLocationData(TypedDict, total=False):
    geolocation: Optional[GeoLocationType]
    state: Optional[TwoCharString]
    country: Optional[TwoCharString]
    postal_code: Optional[Union[str, int]]

