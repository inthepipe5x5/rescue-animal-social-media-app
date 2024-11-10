from marshmallow import Schema, fields, validate
from enum import Enum
from ...db import db

# from ...db import db
from ...package.petfinder_types import AnimalType


class AnimalType(Enum):
# The class `AnimalType` defines an enumeration of different types of animals.
    DOG = "dog"
    CAT = "cat"
    RABBIT = "rabbit"
    SMALL_FURRY = "small-furry"
    HORSE = "horse"
    BIRD = "bird"
    SCALES_FINS_OTHER = "scales-fins-other"
    BARNYARD = "barnyard"


class Animal(db.Model):
    """
    Represents an animal in the database.

    This model stores all information about an animal, including its attributes,
    matching the structure of an returned from PetFinder /animalsAPI response.
    """

    __tablename__ = "animals"

    id = db.Column(db.String(50), primary_key=True)
    type = db.Column(db.Enum(AnimalType), nullable=False)
    name = db.Column(db.String(100))
    breed = db.Column(db.String(100))
    size = db.Column(db.String(20))
    gender = db.Column(db.String(20))
    age = db.Column(db.String(20))
    color = db.Column(db.String(50))
    coat = db.Column(db.String(20))
    status = db.Column(db.String(20))
    organization_id = db.Column(db.String(50))
    description = db.Column(db.Text)

    # Attributes
    spayed_neutered = db.Column(db.Boolean)
    house_trained = db.Column(db.Boolean)
    declawed = db.Column(db.Boolean)
    special_needs = db.Column(db.Boolean)
    shots_current = db.Column(db.Boolean)


class AnimalAttributesSchema(Schema):
    # Attributes
    spayed_neutered = fields.Boolean()
    house_trained = fields.Boolean()
    declawed = fields.Boolean()
    special_needs = fields.Boolean()
    shots_current = fields.Boolean()

class AnimalEnvironmentSchema(Schema):
    # Environment
    children = fields.Boolean()
    dogs = fields.Boolean()
    cats = fields.Boolean()

class AddressSchema(Schema):
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

class BreedsSchema(Schema):
    primary = fields.Str(allow_none=True)
    secondary = fields.Str(allow_none=True)
    mixed = fields.Bool(allow_none=True)
    unknown = fields.Bool(allow_none=True)

class ColorsSchema(Schema):
    primary = fields.Str(allow_none=True)
    secondary = fields.Str(allow_none=True)
    tertiary = fields.Str(allow_none=True)

class AttributesSchema(Schema):
    spayed_neutered = fields.Bool()
    house_trained = fields.Bool()
    declawed = fields.Bool(allow_none=True)
    special_needs = fields.Bool()
    shots_current = fields.Bool()

class EnvironmentSchema(Schema):
    children = fields.Bool()
    dogs = fields.Bool()
    cats = fields.Bool()

class PhotoSchema(Schema):
    small = fields.Url()
    medium = fields.Url()
    large = fields.Url()
    full = fields.Url()

class VideoSchema(Schema):
    embed = fields.Str()

class LinkSchema(Schema):
    href = fields.Url()


class AnimalSchema(Schema):
    """
    Marshmallow schema for serializing and deserializing Animal objects.
    
    This schema matches the structure of the PetFinder API response and is used
    for data validation and formatting.
    """
    id = fields.Int()
    name = fields.Str()
    size = fields.Str()
    gender = fields.Str()
    age = fields.Str()
    breeds = fields.Nested(BreedsSchema)
    colors = fields.Nested(ColorsSchema)
    coat = fields.Str()
    status = fields.Str()
    organization_id = fields.Str()
    description = fields.Str()

    tags = fields.List(fields.Str())
    
    #Nested Boolean (environment, attributes)
    environment = fields.Nested(AnimalEnvironmentSchema)
    attributes = fields.Nested(AnimalAttributesSchema)

    # Additional fields from API response
    #Media
    photos = fields.List(fields.Dict())
    videos = fields.List(fields.Dict())
    contact = fields.Dict()
    _links = fields.Dict()

class PaginationSchema(Schema):
    count_per_page = fields.Int()
    total_count = fields.Int()
    current_page = fields.Int()
    total_pages = fields.Int()
    _links = fields.Dict(keys=fields.Str(), values=fields.Nested(LinkSchema))

class AnimalListResponseSchema(Schema):
    """
    Schema for the entire response from the PetFinder API's /animals endpoint.

    This schema includes a list of animals and pagination information.
    """

    animals = fields.List(fields.Nested(AnimalSchema))
    pagination = fields.Dict()
