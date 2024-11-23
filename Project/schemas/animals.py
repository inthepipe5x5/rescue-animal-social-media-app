import html
from marshmallow import fields, validate, pre_load, post_dump
from Project.services.petfinder.petfinder_types import FormattedAnimalType
from Project.utils.parse import Parse, ParseAnimal
from core import ma
from fuzzywuzzy import process


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


from Project.services import geodb
from Project.schemas.common import (
    PhotoSchema,
    VideoSchema,
    LinkSchema,
    ContactSchema,
    AddressSchema,
)


class AnimalSchema(ma.Schema):
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

        bad_colors_key = ("color", "colors", "colour", "colours")
        for bad_key in bad_colors_key:
            if bad_key in data:
                if "colors" not in data:
                    data["colors"] = ParseAnimal.parse_color(colors_obj=data[bad_key])
                del data[bad_key]
        bad_breeds_key = (
            "breed",
            "BREED",
            "BREEDs",
        )
        for bad_key in bad_breeds_key:
            if bad_key in data:
                if "breeds" not in data:
                    data["breeds"] = ParseAnimal.parse_breed(breeds_obj=data[bad_key])
                del data[bad_key]

        if "environment" in data:
            animal_env_schema = EnvironmentSchema()
            env_data = animal_env_schema.load(data["environment"])
            del data["environment"]
        if "attributes" in data:
            animal_attr_schema = AttributesSchema()
            # deserialize attributes
            attr_data = animal_attr_schema.load(data["attributes"])
            # combine with data
            data = data.extend(attr_data)
            del data["attributes"]

        # deserialize animal
        data = AnimalSchema.deserialize_animal(animal_data=data)

        # html escape the values
        data = (
            {
                key: html.escape(value)
                for key, value in data.items()
                if isinstance(value, str)
            }
            if isinstance(data, dict)
            else data
        )

        return data

    @post_dump
    def postprocess_data(self, data, **kwargs):
        # Convert 'type' to a prettified format for API requests

        if "type" in data:
            data["type"] = process.extractOne(data["type"], Parse.PRETTIFIED_MAPPING)
        return data

    @staticmethod
    def deserialize_address(animal_data):
        """
        Deserialize the address from the animal's contact information and format it for City model.

        :param animal_data: Dict containing animal data from API response
        :return: Dict with deserialized and formatted address information
        """
        if (
            not animal_data
            or "contact" not in animal_data
            or "address" not in animal_data["contact"]
        ):
            return None
        #for animals
        if "contact" in animal_data:
            address_data = animal_data["contact"]["address"]
        #for orgs
        else:
            address_data = animal_data["address"]

        # Use the existing AddressSchema to deserialize the address
        address_schema = AddressSchema()
        deserialized_address = address_schema.load(address_data)

        # Process the deserialized address data to match City model structure
        city_data = {
            "name": deserialized_address.get("city"),
            "country": deserialized_address.get("country"),
            "country_code": deserialized_address.get(
                "country"
            ),  # Assuming country is provided as a code
            "region": deserialized_address.get("state"),
            "region_code": deserialized_address.get(
                "state"
            ),  # Assuming state is provided as a code
            "postcode": deserialized_address.get("postcode"),
        }

        # Use the process_city_data function to format the data for City model
        formatted_city_data = geodb.process_city_data(city_data)

        return formatted_city_data

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

    @staticmethod
    def deserialize_address(animal_data):
        """
        Deserialize the address from the animal's contact information using LinkSchema.

        :param animal_data: Dict containing animal data from API response
        :return: Dict with deserialized address information
        """
        if (
            not animal_data
            or "contact" not in animal_data
            or "address" not in animal_data["contact"]
        ):
            return None

        address_data = animal_data["contact"]["address"]

        # Use LinkSchema to deserialize the _links part if it exists
        if "_links" in address_data:
            link_schema = LinkSchema()
            address_data["_links"] = link_schema.load(address_data["_links"])

        # Deserialize the address data
        address_schema = AddressSchema()
        deserialized_address = address_schema.load(address_data)

        return deserialized_address

    @classmethod
    def deserialize_animal(cls, animal_data):
        """
        Deserialize the entire animal data, including the address.

        :param animal_data: Dict containing animal data from API response
        :return: Dict with fully deserialized animal data
        """
        schema = cls()
        deserialized_data = schema.load(animal_data)

        # Deserialize the address separately
        deserialized_address = cls.deserialize_address(animal_data)
        if deserialized_address:
            deserialized_data["contact"]["address"] = deserialized_address

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

    @pre_load
    def preprocess_data(self, data, **kwargs):
        # Standardize 'type' to lowercasing the prettified animal mapping returned by the API
        if "type" in data:
            data["type"] = Parse.PRETTIFIED_MAPPING.get(data["type"].lower())

        return data


if __name__ == "__main__":
    pass
