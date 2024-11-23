from marshmallow import (
    fields,
    post_dump,
    post_load,
    pre_load,
    validate,
    Schema,
    fields,
    validates_schema,
    ValidationError,
    INCLUDE,
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
    postal_code = fields.Str(allow_none=True)
    country = fields.Str(allow_none=True)

    @pre_load
    def preprocess_data(self, data: Dict[str]) -> Dict[str]:
        if "postcode" in data:
            data["postal_code"] = data["postcode"]
            del data["postcode"]


class ContactSchema(Schema):
    email = fields.Str(allow_none=True)
    phone = fields.Str(allow_none=True)
    address = fields.Nested(AddressSchema, partial=True)

    @post_dump
    def format_address_for_city(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:

        if "address" in data:
            city_data: Dict[str, Optional[str]] = {
                "name": data["address"].get("city"),
                "country": data["address"].get("country"),
                "country_code": data["address"].get("country"),
                "region": data["address"].get("state"),
                "region_code": data["address"].get("state"),
                "postal_code": data["address"].get("postal_code")
                or data["address"].get("postcode"),
            }
            data["address"] = geodb.process_city_data(city_data)
        return data


def reduce_media_dict(data):
    """Helper function to reduce any iterable datatypes to a single entry

    Args:
        data (dict): media_dict
    """
    for value in data.values():
        if isinstance(value, (list, tuple)):
            value = value[0]  # save only first value
        elif isinstance(value, dict):
            value = value.values[0]


class PhotoSchema(ma.Schema):
    small = fields.Url()
    medium = fields.Url()
    large = fields.Url()
    full = fields.Url()

    @pre_load
    def reduce_photos(self, data: dict) -> dict:
        reduce_media_dict(data)


class VideoSchema(ma.Schema):
    embed = fields.Str()

    @pre_load
    def reduce_photos(self, data: dict) -> dict:
        reduce_media_dict(data)


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
