import os
import pytz
from sqlalchemy.orm import declared_attr, class_mapper
from datetime import datetime  # , timezone

# from marshmallow import fields
# from sqlalchemy import Column, Integer, String, Boolean
# from sqlalchemy.dialects.postgresql import JSONB
# from sqlalchemy.orm import Mapped, mapped_column

from core.extensions import db

# class SchemaDbModel(db.Model):
#     __abstract__ = True

#     def __init_subclass__(cls, schema=None):
#         super().__init_subclass__()
#         if schema:
#             cls.create_model_from_schema(schema)

#     @classmethod
#     def create_model_from_schema(cls, schema_class):
#         for field_name, field_obj in schema_class._declared_fields.items():
#             column = cls.get_column_from_field(field_obj)
#             column = setattr(cls, field_name, column) if column else None

#     @staticmethod
#     def get_column_from_field(field_obj):
#         if isinstance(field_obj, fields.Int):
#             return Column(Integer)
#         elif isinstance(field_obj, fields.Str):
#             return Column(String)
#         elif isinstance(field_obj, fields.Boolean):
#             return Column(Boolean)
#         elif isinstance(field_obj, fields.Url):
#             return Column(String)
#         elif isinstance(field_obj, fields.Nested):
#             return Column(JSONB)
#         elif isinstance(field_obj, fields.List):
#             if isinstance(field_obj.inner, fields.Str):
#                 return Column(JSONB)  # Store list of strings as JSONB
#         else:
#             return Column(String)  # Default to String

#     @classmethod
#     def validate_data(cls, data):
#         schema = cls.schema()
#         errors = schema.validate(data)
#         if errors:
#             raise ValueError(f"Invalid data: {errors}")
#         return schema.load(data)

#     @classmethod
#     def db_bulk_insert_mapping(cls, api_response):
#         schema = cls.schema()
#         try:
#             validated_data = schema.load(api_response)
#         except ValueError as e:
#             print(f"Validation error: {e}")
#             return

#         data_to_insert = []
#         for item in validated_data.get(cls.api_list_key, []):
#             try:
#                 validated_item = cls.validate_data(item)
#                 data_to_insert.append(cls(**validated_item))
#             except ValueError as e:
#                 print(f"Skipping invalid item: {e}")

#         if data_to_insert:
#             db.session.bulk_save_objects(data_to_insert)
#             db.session.commit()
#         else:
#             print("No valid data to insert")

#     @staticmethod
#     def get_next_url(pagination_data):
#         if not pagination_data or "_links" not in pagination_data:
#             return None

#         next_link = pagination_data["_links"].get("next")
#         if next_link and "href" in next_link:
#             return next_link["href"]
#         return None


class MetaDataMixin:
    """Db Model Mixin for stored DB"""

    __abstract__ = True

    dt_saved = db.Column(
        db.DateTime,
        default=datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S %Z%z"),
        onupdate=datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S %Z%z"),
    )
    provider = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        """Deserializes instance to a python dict.

        Returns:
            dict: deserialized db columns
        """
        return {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }

    @staticmethod
    def set_provider(target, value, oldvalue, initiator):
        if not value:
            if target.__tablename__.casefold() in ("animals", "rescueorg"):
                target.provider = "petfinder"
            elif target.__tablename__.casefold() == "cities":
                target.provider = "geodb_cities"
            else:
                target.provider = "unknown"  # Unknown provider

    db.event.listen(provider, "set", set_provider)

    @property
    def base_url(self):
        """Returns the base URL for the provider, or None if unknown."""
        base_urls = {
            "petfinder": os.environ.get(
                "PETFINDER_API_URL", "https://api.petfinder.com/v2"
            ),
            "geodb_cities": os.environ.get(
                "GEODB_CITIES_API_URL", "https://wft-geo-db.p.rapidapi.com/v1/geo"
            ),
        }
        return base_urls.get(self.provider.casefold(), None)
