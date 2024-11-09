from marshmallow import Schema, fields, validate

class OrganizationRequestSchema(Schema):
    name = fields.Str()
    location = fields.Str()
    distance = fields.Int(validate=validate.Range(min=1, max=500), missing=100)
    state = fields.Str(validate=validate.Length(equal=2))
    country = fields.Str(validate=validate.Length(equal=2))
    query = fields.Str()
    sort = fields.Str(validate=validate.OneOf(["distance", "-distance", "name", "-name", "country", "-country", "state", "-state"]))
    limit = fields.Int(validate=validate.Range(min=1, max=100), missing=20)
    page = fields.Int(validate=validate.Range(min=1), missing=1)