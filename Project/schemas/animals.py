import html
from typing import Optional
from fuzzywuzzy import process
from marshmallow import fields, post_load, validate, pre_load, post_dump
from Project.services.petfinder.petfinder_types import FormattedAnimalType
from Project.utils.parse import Parse, ParseAnimal
from Project.core.extensions import ma
from Project.services import geodb
from Project.schemas.common import (
    PetFinderResponseSchema,
    PhotoSchema,
    VideoSchema,
    LinkSchema,
    ContactSchema,
    AddressSchema,
)


class DefaultedBooleanField(fields.Boolean):
    """Custom boolean field that handles falsy values by default setting to False if falsy

    Args:
        fields (_type_): _description_
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, falsy=["null", "none", "None"], default=False, **kwargs)


class DefaultedStringField(fields.String):
    """Custom String field that handles falsy values by default setting to str:"Unknown" if falsy

    Args:
        fields (_type_): _description_
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, falsy=["null", "none", "None"], default="Unknown", **kwargs
        )


class AnimalAttributesSchema(ma.Schema):
    # Attributes
    spayed_neutered = DefaultedBooleanField()
    house_trained = DefaultedBooleanField()
    declawed = DefaultedBooleanField()
    special_needs = DefaultedBooleanField()
    shots_current = DefaultedBooleanField()


class BreedsSchema(ma.Schema):
    primary = DefaultedStringField()
    secondary = DefaultedStringField()
    mixed = DefaultedBooleanField()
    unknown = DefaultedBooleanField()


class ColorsSchema(ma.Schema):
    primary = DefaultedStringField()
    secondary = DefaultedStringField()
    tertiary = DefaultedStringField()


class AttributesSchema(ma.Schema):
    spayed_neutered = DefaultedBooleanField()
    house_trained = DefaultedBooleanField()
    declawed = DefaultedBooleanField()
    special_needs = DefaultedBooleanField()
    shots_current = DefaultedBooleanField()


class EnvironmentSchema(ma.Schema):
    children = DefaultedBooleanField()
    dogs = DefaultedBooleanField()
    cats = DefaultedBooleanField()


class EnvironmentSchema(ma.Schema):
    children = DefaultedBooleanField()
    dogs = DefaultedBooleanField()
    cats = DefaultedBooleanField()


@post_load
def add_friendly_suffix(self, data: dict, **kwargs) -> Optional[dict[str]]:
    """Add friendly suffix to EnvironmentSchema keys to match values used by db

    Args:
        data (dict): validated animal environment data from pf api

    Returns:
        Optional[dict[str]]: _description_
    """
    return {f"{key}_friendly": value for key, value in data.items()}


class AnimalSchema(PetFinderResponseSchema):
    """
    Marshmallow ma.Schema for serializing and deserializing Animal objects.

    This ma.Schema matches the structure of the PetFinder API response and is used
    for data validation and formatting.
    """

    id = fields.Int()
    organization_id = fields.Str()
    type = fields.Enum(FormattedAnimalType)
    name = fields.Str()
    size = fields.Str()
    gender = fields.Str()
    age = fields.Str()
    # Features
    breeds = fields.Nested(BreedsSchema)
    colors = fields.Nested(ColorsSchema)
    coat = fields.Str()
    status = fields.Str()
    description = fields.Str()

    tags = fields.List(fields.Str())

    # Nested Boolean (environment, attributes)
    environment = fields.Nested(EnvironmentSchema)
    attributes = fields.Nested(AnimalAttributesSchema)

    # Additional fields from API response
    # Media
    photos = fields.Nested(PhotoSchema)
    videos = fields.Nested(VideoSchema)
    contact = fields.Nested(ContactSchema)
    # _links are handled in parent schema class

    @pre_load
    def preprocess_animal(self, data, **kwargs):
        """
        Schema Pre-load Function to flatten animal response from PetFinder API

        Method: The function preprocesses animal data by mapping type values, parsing colors and breeds, and
        then calling the superclass method to complete the preprocessing.

        :param data: The `data` parameter in the `preprocess_animal` method contains information about
        an animal, such as its type, colors, and breeds. The method processes this data by converting
        the type field to a standardized format, parsing colors and breeds using specific parser
        functions, and then calling the `pre
        :return: The `preprocess_animal` method is returning the result of calling the `preprocess_data`
        method of the superclass with the processed `data` and any additional `kwargs`.
        """
        # Process type field
        self._preprocess_field(
            data,
            "type",
            "types",
            "animal_type",
            "animal_types",
            parser_func=ParseAnimal.reverse_prettify_animal_types,
            target_key="type",
        )

        # Process colors and breeds
        self._preprocess_field(
            data,
            "color",
            "colors",
            "colour",
            "colours",
            parser_func=ParseAnimal.parse_color,
            target_key="colors",
        )
        # Handle "breeds" field
        self._preprocess_field(
            data,
            "breed",
            "BREED",
            "BREEDs",
            parser_func=ParseAnimal.parse_breed,
            target_key="breeds",
        )

        # Handle "environment" field
        self._preprocess_field(
            data,
            "environment",
            target_key="environment",
            parser_func=lambda x: EnvironmentSchema().load(x),
            remove_source_keys=True,
        )

        # Handle "attributes" field
        self._preprocess_field(
            data,
            "attributes",
            target_key="attributes",
            parser_func=lambda x: AttributesSchema().load(x),
            remove_source_keys=True,
        )
        # Define keys exempt from sanitization
        exempt_keys = ["id", "name", "organization_id", "description"]

        # Sanitize string fields
        for key, value in data.items():
            if key not in exempt_keys:
                data[key] = (
                    self._sanitize_string(value)
                    if isinstance(value, str) and value
                    else value
                )
            elif isinstance(value, str):
                # Apply HTML escape but keep original casing
                data[key] = html.escape(value)

        return super().preprocess_data(data, **kwargs)

    @classmethod
    def deserialize_animal(cls, animal_data):
        """
        Deserialize the entire animal data, including the address formatted for City model.

        :param animal_data: Dict containing animal data from API response
        :return: Dict with fully deserialized animal data
        """
        schema = cls()
        deserialized_data = schema.load(animal_data)

        # Deserialize and format the address separately
        formatted_address = cls.deserialize_address(animal_data)
        if formatted_address:
            deserialized_data["contact"]["address"] = formatted_address

        return deserialized_data


class AnimalListResponseSchema(ma.Schema):
    """
    ma.Schema for the entire response from the PetFinder API's /animals endpoint.

    This ma.Schema includes a list of animals and pagination information.
    """

    animals = fields.List(fields.Nested(AnimalSchema))
    pagination = fields.Dict()


class AnimalCityJoinSchema(ma.Schema):
    animal_id = fields.String(attribute="Animal.id")
    animal_name = fields.String(attribute="Animal.name")
    animal_type = fields.String(attribute="Animal.type")
    city_name = fields.String(attribute="City.name")
    city_country = fields.String(attribute="City.country")
    city_geolocation = fields.String(attribute="City.geolocation")


####################################### GET Request Schemas
from Project.core.constants import (
    default_animal_age_choices,
    default_animal_gender_choices,
    default_animal_size_choices,
    default_animal_status_choices,
)


class AnimalRequestSchema(ma.Schema):
    status = fields.List(
        fields.Str(
            allow_none=True, validate=validate.OneOf(default_animal_status_choices)
        )
    )
    name = DefaultedStringField()
    type = fields.Str(allow_none=True, validate=validate.OneOf(FormattedAnimalType))
    breed = fields.List(DefaultedStringField())
    size = fields.List(
        fields.Str(
            allow_none=True, validate=validate.OneOf(default_animal_size_choices)
        )
    )
    gender = fields.List(
        fields.Str(
            allow_none=True, validate=validate.OneOf(default_animal_gender_choices)
        )
    )
    age = fields.List(
        fields.Str(allow_none=True, validate=validate.OneOf(default_animal_age_choices))
    )
    color = fields.Str(allow_none=True)
    coat = fields.List(
        fields.Str(
            allow_none=True,
            validate=validate.OneOf(
                ["short", "medium", "long", "wire", "hairless", "curly"]
            ),
        )
    )
    organization = fields.List(DefaultedStringField())
    good_with_children = DefaultedBooleanField
    good_with_dogs = DefaultedBooleanField
    good_with_cats = DefaultedBooleanField
    house_trained = DefaultedBooleanField
    declawed = DefaultedBooleanField
    special_needs = DefaultedBooleanField

    # geography
    location = fields.Str(allow_none=False)  # mandatory
    distance = fields.Int(validate=validate.Range(min=1, max=500))

    # meta
    before = fields.DateTime(format="iso", allow_none=True)
    after = fields.DateTime(format="iso", allow_none=True)
    sort = fields.Str(
        validate=validate.OneOf(
            ["recent", "-recent", "distance", "-distance", "random"]
        )
    )
    page = fields.Int(validate=validate.Range(min=1))
    limit = fields.Int(validate=validate.Range(min=1, max=100))

    @pre_load
    def preprocess_data(self, data, **kwargs):
        # Standardize 'type' to lowercasing the prettified animal mapping returned by the API
        if "type" in data:
            data["type"] = Parse.PRETTIFIED_MAPPING.get(data["type"].lower())

        return data


if __name__ == "__main__":
    pass
