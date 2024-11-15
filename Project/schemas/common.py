from marshmallow import fields, validate
from core import ma


class AddressSchema(ma.Schema):
    address1 = fields.Str(allow_none=True)
    address2 = fields.Str(allow_none=True)
    city = fields.Str(allow_none=True)
    state = fields.Str(allow_none=True)
    postcode = fields.Str(allow_none=True)
    country = fields.Str(allow_none=True)


class ContactSchema(ma.Schema):
    email = fields.Str(allow_none=True)
    phone = fields.Str(allow_none=True)
    address = fields.Nested(AddressSchema)


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
