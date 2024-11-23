from marshmallow import ValidationError, fields, Schema, post_load, pre_load
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from Project.services.geography.util import GeoUtil
from Project.utils.utils import TwoCharString
from Project.core.types import GeoLocationType
from Project.core.extensions import db


class CitySchema(Schema):
    """Schema for API City locations

    Args:
        Schema (_type_): _description_

    Raises:
        ValueError: _description_
        ValueError: _description_

    Returns:
        _type_: _description_
    """

    type = fields.String(required=True, default="CITY")
    name = fields.String(required=True)
    country = fields.String(required=False)
    region_name = fields.String(required=False)
    region_code = fields.String(required=False)
    population = fields.Integer(required=False)
    postal_code = fields.String(required=False)
    country_code = fields.String(validate=TwoCharString())
    region_code = fields.String(validate=TwoCharString())
    # Assuming GeoLocationType is a custom field type
    geolocation = GeoLocationType()

    @pre_load
    def preprocess_data(self, data, **kwargs):
        return self.process_city_data(city_data=data)

    @post_load
    def make_city(self, data, **kwargs):
        """Save data to a City db.Model class instance and save to

        Args:
            data (_type_): _description_

        Returns:
            _type_: _description_
        """
        return self.save_new_city(data=data)

    @classmethod
    def process_city_data(city_data: dict):
        """
        Process the city data returned by the API to match the City db.model structure.

        :param city_data: The data returned by the API
        :param state: The state name (since it might not be included in the API response)
        :return: A dictionary with keys matching the City db.model
        """
        # de-serialize if nested data
        nesting_keys = ["contact", "address"]
        for key in nesting_keys:
            if key in city_data:
                city_data = city_data.get(key, city_data)

        # format geolocation
        if "geolocation" in city_data:
            geolocation = city_data.get("geolocation", None)
        else:
            geolocation = (
                f"({city_data.get('latitude', '')},{city_data.get('longitude', '')})"
                if ("latitude" in city_data and "longitude" in city_data)
                else None
            )
        geolocation = (
            CitySchema.format_geolocation(coordinates=geolocation)
            if geolocation
            else None
        )

        processed_data = {
            "type": "CITY",
            "name": city_data.get("name") or city_data.get("city"),
            "country": city_data.get("country") or city_data.get("countryCode"),
            "country_code": city_data.get(
                "countryCode"
            )  # countryCode and regionCode are returned from GeoDB API
            or city_data.get("country_code"),
            "region_name": city_data.get("state")
            or city_data.get("region")
            or city_data.get("region", None),
            "region_code": city_data.get("regionCode")
            or city_data.get("region_code")
            or city_data.get("iso_code")
            or city_data.get("isoCode", None),
            "geolocation": geolocation,
            "population": city_data.get("population", None),
            "postal_code": city_data.get("postal_code")
            or city_data.get("postcode", None),
        }
        # Normalize processed data using pycountry
        for key, value in processed_data.items():
            if value:
                processed_data[key] = GeoUtil.normalize_to_pycountry(value, key)

        return processed_data

    @staticmethod
    def format_geolocation(*coordinates) -> str:
        """
        This function formats geolocation coordinates into a standardized string format.
        It can handle a single string input, separate float inputs, or separate string inputs for latitude and longitude.

        Args:
            *coordinates: Either a single string "latitude,longitude" or two values (latitude, longitude) as floats or strings

        Returns:
            str: geolocation string in "latitude,longitude" format with 6 decimal places precision

        Examples:
            >>> format_geolocation("43.6429,79.3889")
            '43.642900,79.388900'
            >>> format_geolocation(40.7128, -74.0060)
            '40.712800,-74.006000'
            >>> format_geolocation("-33.8688", "151.2093")
            '-33.868800,151.209300'
        """
        if len(coordinates) == 1 and isinstance(coordinates[0], str):
            # Handle single string input
            lat, lon = map(float, coordinates[0].split(","))
        elif len(coordinates) == 2:
            # Handle separate inputs (float or string)
            try:
                lat, lon = map(float, coordinates)
            except ValueError:
                raise ValueError(
                    "Invalid input. Latitude and longitude must be convertible to float."
                )
        else:
            raise ValueError(
                "Invalid input. Provide either a string 'latitude,longitude' or two values (float or string)."
            )

        return f"{lat:.6f},{lon:.6f}"
