from marshmallow import fields, validate, pre_load, post_dump
from Project.services.petfinder.petfinder_types import FormattedAnimalType
from Project.utils.parse import Parse
from core import ma


class AnimalAttributesSchema(ma.Schema):
    # Attributes
    spayed_neutered = fields.Boolean(allow_none=True)
    house_trained = fields.Boolean(allow_none=True)
    declawed = fields.Boolean(allow_none=True)
    special_needs = fields.Boolean(allow_none=True)
    shots_current = fields.Boolean(allow_none=True)


class AnimalEnvironmentSchema(ma.Schema):
    # Environment
    children = fields.Boolean(allow_none=True)
    dogs = fields.Boolean(allow_none=True)
    cats = fields.Boolean(allow_none=True)


class BreedsSchema(ma.Schema):
    primary = fields.Str(allow_none=True)
    secondary = fields.Str(allow_none=True)
    mixed = fields.Bool(allow_none=True)
    unknown = fields.Bool(allow_none=True)


class ColorsSchema(ma.Schema):
    primary = fields.Str(allow_none=True)
    secondary = fields.Str(allow_none=True)
    tertiary = fields.Str(allow_none=True)


class AttributesSchema(ma.Schema):
    spayed_neutered = fields.Bool()
    house_trained = fields.Bool()
    declawed = fields.Bool(allow_none=True)
    special_needs = fields.Bool()
    shots_current = fields.Bool()


class EnvironmentSchema(ma.Schema):
    children = fields.Bool()
    dogs = fields.Bool()
    cats = fields.Bool()


from .common import PhotoSchema, VideoSchema, LinkSchema, ContactSchema


class AnimalSchema(ma.Schema):
    """
    Marshmallow ma.Schema for serializing and deserializing Animal objects.

    This ma.Schema matches the structure of the PetFinder API response and is used
    for data validation and formatting.
    """

    id = fields.Int()
    name = fields.Str()
    size = fields.Str()
    gender = fields.Str()
    age = fields.Str()
    # Features
    breeds = fields.Nested(BreedsSchema)
    colors = fields.Nested(ColorsSchema)
    coat = fields.Str()
    status = fields.Str()
    organization_id = fields.Str()
    description = fields.Str()

    tags = fields.List(fields.Str())

    # Nested Boolean (environment, attributes)
    environment = fields.Nested(AnimalEnvironmentSchema)
    attributes = fields.Nested(AnimalAttributesSchema)

    # Additional fields from API response
    # Media
    photos = fields.Nested(PhotoSchema)
    videos = fields.Nested(VideoSchema)
    contact = fields.Nested(ContactSchema)
    _links = fields.Nested(LinkSchema)

    @pre_load
    def preprocess_data(self, data, **kwargs):
        # Standardize 'type' to lowercase by reverse the prettified animal mapping
        mapping = {value: key for key, value in Parse.PRETTIFIED_MAPPING.items()}

        if "type" in data:
            data["type"] = mapping.get(data["type"].lower())
        return data

    @post_dump
    def postprocess_data(self, data, **kwargs):
        # Convert 'type' to a prettified format for API requests

        if "type" in data:
            data["type"] = Parse.prettify_animal_types(data["type"])
        return data


class AnimalListResponseSchema(ma.Schema):
    """
    ma.Schema for the entire response from the PetFinder API's /animals endpoint.

    This ma.Schema includes a list of animals and pagination information.
    """

    animals = fields.List(fields.Nested(AnimalSchema))
    pagination = fields.Dict()


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
    name = fields.Str(allow_none=True)
    type = fields.Str(allow_none=True, validate=validate.OneOf(FormattedAnimalType))
    breed = fields.List(fields.Str(allow_none=True))
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
    organization = fields.List(fields.Str(allow_none=True))
    good_with_children = fields.Boolean(allow_none=True)
    good_with_dogs = fields.Boolean(allow_none=True)
    good_with_cats = fields.Boolean(allow_none=True)
    house_trained = fields.Boolean(allow_none=True)
    declawed = fields.Boolean(allow_none=True)
    special_needs = fields.Boolean(allow_none=True)

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


if __name__ == "__main__":
    pass
