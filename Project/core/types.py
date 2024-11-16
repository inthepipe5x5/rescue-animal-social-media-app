from typing import TypedDict, Optional, Union


class GeoLocation(TypedDict):
    latitude: float
    longitude: float


# This Union type allows for both dictionary and string representations of geolocation
GeoLocationType = Union[GeoLocation, str]  # str for "lat,lon" format


class UserLocationData(TypedDict, total=False):
    from Project.utils.utils import TwoCharString

    geolocation: Optional[GeoLocationType]
    state: Optional[TwoCharString]
    country: Optional[TwoCharString]
    postal_code: Optional[Union[str, int]]
