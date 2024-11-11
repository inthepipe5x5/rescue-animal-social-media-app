from marshmallow import fields, validate
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
    #Features
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





class AnimalListResponseSchema(ma.Schema):
    """
    ma.Schema for the entire response from the PetFinder API's /animals endpoint.

    This ma.Schema includes a list of animals and pagination information.
    """

    animals = fields.List(fields.Nested(AnimalSchema))
    pagination = fields.Dict()

####################################### GET Request Schemas 
class AnimalRequestSchema(ma.Schema):
    status = fields.List(fields.Str(validate=validate.OneOf(["adoptable", "adopted", "found"])))
    name = fields.Str()
    type = fields.Str(validate=validate.OneOf(["dog", "cat", "rabbit", "small-furry", "horse", "bird", "scales-fins-other", "barnyard"]))
    breed = fields.List(fields.Str())
    size = fields.List(fields.Str(validate=validate.OneOf(["small", "medium", "large", "xlarge"])))
    gender = fields.List(fields.Str(validate=validate.OneOf(["male", "female", "unknown"])))
    age = fields.List(fields.Str(validate=validate.OneOf(["baby", "young", "adult", "senior"])))
    color = fields.Str()
    coat = fields.List(fields.Str(validate=validate.OneOf(["short", "medium", "long", "wire", "hairless", "curly"])))
    organization = fields.List(fields.Str())
    good_with_children = fields.Boolean()
    good_with_dogs = fields.Boolean()
    good_with_cats = fields.Boolean()
    house_trained = fields.Boolean()
    declawed = fields.Boolean()
    special_needs = fields.Boolean()
    
    #geography
    location = fields.Str()
    distance = fields.Int(validate=validate.Range(min=1, max=500))
    
    #meta
    before = fields.DateTime(format="iso")
    after = fields.DateTime(format="iso")
    sort = fields.Str(validate=validate.OneOf(["recent", "-recent", "distance", "-distance", "random"]))
    page = fields.Int(validate=validate.Range(min=1))
    limit = fields.Int(validate=validate.Range(min=1, max=100))


if __name__ == '__main__':
    pass