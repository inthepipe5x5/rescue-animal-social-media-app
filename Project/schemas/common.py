import html
from marshmallow import (
    fields,
    post_dump,
    pre_load,
    validate,
    Schema,
    fields,
)
from typing import Dict, Any, Optional, Tuple, List, Union
from Project.services import geodb
from Project.utils.utils import get_nested_value


class NestedSchemaMixin(Schema):
    """A SchemaMixin to provide methods for deserializing nested values"""

    def get_value(
        self, data, target_key: str, nesting_keys: Optional[List[str]] = None
    ) -> Any:

        data = self.__dict__ if not data else data

        return get_nested_value(
            data=self.__dict__, target_key=target_key, nesting_keys=nesting_keys
        )

    
    @staticmethod
    def _sanitize_string(value):
        """
        Sanitize strings by stripping whitespace, decoding HTML entities, and escaping malicious input.
        """
        if not value or not isinstance(value, str):
            return value

        # Decode HTML entities to prevent double escaping
        decoded_value = html.unescape(value.strip())

        # Escape any malicious input
        sanitized_value = html.escape(decoded_value)

        return sanitized_value

class AddressSchema(NestedSchemaMixin):
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


class ContactSchema(NestedSchemaMixin):
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


def reduce_media_dict(
    data: Dict[str, Any],
    nesting_keys: Tuple[str, ...] = ("embed", "href"),
    order_keys: List[str] = [
        "full",
        "primary",
        "large",
        "primary_cropped",
        "medium",
        "small",
    ],
) -> Union[str, int, float, bool, None]:
    """Helper function to reduce any iterable datatypes to a single entry

    Args:
        data (Dict[str, Any]): media_dict
        nesting_keys (Tuple[str, ...]): Keys to follow for nested structures (default: ("embed", "href"))
        order_keys (List[str]): List of keys to prioritize if dict (default: ["full", "primary", "primary_cropped", "large", "medium", "small"])

    Returns:
        Union[str, int, float, bool, None]: The reduced value
    """
    if isinstance(data, list) and len(data) > 0:
        return reduce_media_dict(data[0], nesting_keys, order_keys)

    if not isinstance(data, dict):
        return data

    for key in order_keys:
        if key in data:
            return data[key]

    for key, value in data.items():
        if key in nesting_keys:
            return reduce_media_dict(value, nesting_keys, order_keys)
        elif isinstance(value, (dict, list)):
            return reduce_media_dict(value, nesting_keys, order_keys)
        else:
            return value

    return data if data else None


class PhotoSchema(NestedSchemaMixin):
    small = fields.Url()
    medium = fields.Url()
    large = fields.Url()
    full = fields.Url()

    @pre_load
    def reduce_photos(self, data: dict) -> dict:
        reduce_media_dict(data)


class VideoSchema(NestedSchemaMixin):
    embed = fields.Str()

    @pre_load
    def reduce_photos(self, data: dict) -> dict:
        reduce_media_dict(data)


_LINK_SOURCE_KEYS = [
    "self",
    "animals",
    "animal",
    "organization",
    "next",
    "organization",
    "organizations",
    "type",
]


class LinkSchema(NestedSchemaMixin):
    """
    Schema for deserializing pagination data in PetFinder API GET requests.
    Supports dynamic keys for flexible API responses.
    """

    href = fields.Url(required=True)

    @pre_load
    def normalize_links(self, data, **kwargs):
        # Sanitize and standardize link structure
        if isinstance(data, dict) and "href" in data:
            return self.get_value(
                data=data,
                target_key="href",
                nesting_keys=_LINK_SOURCE_KEYS,
            )
        return data


class PaginationSchema(NestedSchemaMixin):
    """
    Schema for deserializing pagination data in PetFinder API GET requests.
    """

    count_per_page = fields.Int()
    total_count = fields.Int()
    current_page = fields.Int()
    total_pages = fields.Int()
    _links = fields.Dict(keys=fields.Str(), values=fields.Nested(LinkSchema))


class DistanceParamSchema(NestedSchemaMixin):
    distance = fields.Int(validate=validate.Range(min=1, max=500), missing=100)


class limitParamSchema(NestedSchemaMixin):
    distance = fields.Int(validate=validate.Range(min=1, max=100), missing=100)


class PetFinderResponseSchema(NestedSchemaMixin):
    """
    Base Schema for shared logic and fields in PetFinder API responses.
    """

    id = fields.Int()
    organization_id = fields.Str()
    name = fields.Str()
    _links = (
        fields.Dict()
    )  # Leave as Dict for flexibility; will process separately instead of the previous fields.Nested(LinkSchema)

    # @pre_load
    # def preprocess_data(self, data, **kwargs):
    #     # Standardize strings
    #     for key, value in data.items():
    #         if isinstance(value, str):
    #             data[key] = self._sanitize_string(value)

    #     # Process `_links`
    #     if "_links" in data:
    #         data["_links"] = self.deserialize_links(data["_links"])

    #     return data


    def deserialize_address(self, data: dict) -> dict[str]:
        """
        Deserialize the address field for both animals and organizations.
        Handles nested fields (`contact.address` for animals, `address` for orgs).
        :param data(dict): Input data (animal or org)
        :return: Formatted address dictionary or None
        """
        address_data = self.get_value(
            target_key="address", nesting_keys=["contact"]  # for Animal.contact.address
        ) or self.get_value(
            target_key="address"
        )  # for Orgs.address

        if not address_data:
            return None

        # Handle nested `_links` in address if present
        if "_links" in address_data:
            address_data["_links"] = self.deserialize_links(address_data["_links"])

        # Deserialize address using AddressSchema
        address_schema = AddressSchema()
        return address_schema.load(address_data)

    @staticmethod
    def deserialize_links(links_data: dict) -> dict:
        """
        Deserialize `_links` data using LinkSchema, supporting dynamic keys.
        :param links_data: Dict of links data
        :return: Dict with deserialized link data
        """
        if not links_data:
            return None
        link_schema = LinkSchema()
        return {key: link_schema.load(value) for key, value in links_data.items()}
    
    @staticmethod
    def _preprocess_field (
        data: dict,
        target_key: str,
        *source_keys,
        parser_func=None,
        exempt_keys: Optional[List[str]] = None,
        remove_source_keys: bool = True,
    ) -> dict:
        """
        Process and consolidate fields into a target key, handling exceptions and key removal.

        Args:
            data (dict): The input data dictionary.
            target_key (str): The key to consolidate values into.
            *source_keys (str): Keys to retrieve and process values from.
            parser_func (callable, optional): A function to process the field values.
            exempt_keys (list, optional): Keys to exclude from certain operations (e.g., sanitization).
            remove_source_keys (bool): Whether to delete source keys after processing.

        Returns:
            dict: The updated data dictionary.
        """
        exempt_keys = exempt_keys or []

        for key in source_keys:
            try:
                value = data.get(key)
                if value is not None:
                    # Skip exempt keys
                    if key in exempt_keys:
                        data[target_key] = value
                    else:
                        data[target_key] = parser_func(value) if parser_func else value

                    # Remove the source key if specified
                    if remove_source_keys:
                        del data[key]
            except Exception as e:
                # Handle exceptions gracefully and log (if needed)
                print(f"Error processing key '{key}': {e}")
        return data



if __name__ == "__main__":
    pass
