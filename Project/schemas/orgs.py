from marshmallow import fields, pre_load, validate
from Project.core.extensions import ma
from Project.schemas.common import AddressSchema, ContactSchema, LinkSchema, PetFinderResponseSchema


class OrganizationRequestSchema(ma.Schema):
    name = fields.Str()
    location = fields.Str()
    distance = fields.Int(validate=validate.Range(min=1, max=500), missing=100)
    state = fields.Str(validate=validate.Length(equal=2))
    country = fields.Str(validate=validate.Length(equal=2))

    query = fields.Str()
    sort = fields.Str(
        validate=validate.OneOf(
            [
                "distance",
                "-distance",
                "name",
                "-name",
                "country",
                "-country",
                "state",
                "-state",
            ]
        )
    )
    limit = fields.Int(validate=validate.Range(min=1, max=100), missing=20)
    page = fields.Int(validate=validate.Range(min=1), missing=1)


class OrgResponseSchema(PetFinderResponseSchema):
    """
    Schema for deserializing organization data.
    """
    website = LinkSchema()
    mission_statement = fields.String()

    address = fields.Method(deserialize="get_deserialized_address")
    contact = fields.Nested(ContactSchema)

    @pre_load
    def preprocess_org(self, data, **kwargs):
        # Process organization-specific fields if necessary
        return super().preprocess_data(data, **kwargs)

    def get_deserialized_address(self, data):
        """Deserialize the address for animals using the super.deserialize_address(data)"""
        return self.deserialize_address(data)
