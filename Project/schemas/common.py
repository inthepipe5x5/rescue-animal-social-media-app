from marshmallow import (
    fields,
    post_dump,
    validate,
    Schema,
    fields,
    validates_schema,
    ValidationError,
)
from Project.core.extensions import ma
from Project.services import geodb
from typing import Dict, Any, Optional
from fuzzywuzzy import fuzz
import pycountry


class AddressSchema(ma.Schema):
    address1 = fields.Str(allow_none=True)
    address2 = fields.Str(allow_none=True)
    city = fields.Str(allow_none=True)
    state = fields.Str(allow_none=True)
    postcode = fields.Str(allow_none=True)
    country = fields.Str(allow_none=True)

class ContactSchema(Schema):
    email = fields.Str(allow_none=True)
    phone = fields.Str(allow_none=True)
    address = fields.Nested(AddressSchema)

    @staticmethod
    def check_dicts(data: Dict[str, Any], expected: Dict[str, Any]) -> bool:
        def normalize(value: Any, key: str) -> Any:
            if isinstance(value, str):
                value = value.casefold()
                if key in ["country", "countryCode"]:
                    try:
                        country = pycountry.countries.search_fuzzy(value)
                        if country:
                            return country[0].alpha_2
                    except LookupError:
                        pass
                elif key in ["region", "regionCode"]:
                    try:
                        subdivision = pycountry.subdivisions.search_fuzzy(value)
                        if subdivision:
                            return subdivision[0].code
                    except LookupError:
                        pass
            return value

        def fuzzy_match(val1: Any, val2: Any) -> bool:
            if isinstance(val1, str) and isinstance(val2, str):
                return fuzz.ratio(val1, val2) >= 90  # Adjust threshold as needed
            return val1 == val2

        if set(data.keys()) != set(expected.keys()):
            return False

        for key in data:
            if (
                key == "address"
                and isinstance(data[key], dict)
                and isinstance(expected[key], dict)
            ):
                if not ContactSchema.check_dicts(data[key], expected[key]):
                    return False
            else:
                data_value = normalize(data[key], key)
                expected_value = normalize(expected[key], key)
                if not fuzzy_match(data_value, expected_value):
                    return False

        return True

    @validates_schema
    def validate_data(self, data: Dict[str, Any], **kwargs: Any) -> None:
        expected: Dict[str, Any] = {
            "email": "example@email.com",
            "phone": "+1234567890",
            "address": {
                "city": "New York",
                "country": "United States",
                "state": "NY",
                "postcode": "10001",
            },
        }

        if not self.check_dicts(data, expected):
            raise ValidationError("Data does not match expected values")

    @post_dump
    def format_address_for_city(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        if "address" in data:
            city_data: Dict[str, Optional[str]] = {
                "name": data["address"].get("city"),
                "country": data["address"].get("country"),
                "countryCode": data["address"].get("country"),
                "region": data["address"].get("state"),
                "regionCode": data["address"].get("state"),
                "postcode": data["address"].get("postcode"),
            }
            data["address"] = geodb.process_city_data(city_data)
        return data


class PhotoSchema(ma.Schema):
    small = fields.Url()
    medium = fields.Url()
    large = fields.Url()
    full = fields.Url()


class VideoSchema(ma.Schema):
    embed = fields.Str()


class LinkSchema(ma.Schema):
    href = fields.Url()


class PaginationSchema(ma.Schema):
    count_per_page = fields.Int()
    total_count = fields.Int()
    current_page = fields.Int()
    total_pages = fields.Int()
    _links = fields.Dict(keys=fields.Str(), values=fields.Nested(LinkSchema))


class DistanceParamSchema(ma.Schema):
    distance = fields.Int(validate=validate.Range(min=1, max=500), missing=100)


class limitParamSchema(ma.Schema):
    distance = fields.Int(validate=validate.Range(min=1, max=100), missing=100)


if __name__ == "__main__":
    pass
