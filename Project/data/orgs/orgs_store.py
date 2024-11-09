from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

db = SQLAlchemy()
ma = Marshmallow()

class Organization(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String)
    phone = db.Column(db.String)
    url = db.Column(db.String)
    website = db.Column(db.String)
    mission_statement = db.Column(db.Text)
    distance = db.Column(db.Float)

class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.String, db.ForeignKey('organization.id'))
    address1 = db.Column(db.String)
    address2 = db.Column(db.String)
    city = db.Column(db.String)
    state = db.Column(db.String)
    postcode = db.Column(db.String)
    country = db.Column(db.String)

class OrganizationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Organization
        include_fk = True

class AddressSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Address
        include_fk = True

class OrganizationResponseSchema(ma.Schema):
    id = fields.Str()
    name = fields.Str()
    email = fields.Email()
    phone = fields.Str()
    address = fields.Nested(AddressSchema)
    hours = fields.Dict(keys=fields.Str(), values=fields.Str())
    url = fields.Url()
    website = fields.Url(allow_none=True)
    mission_statement = fields.Str(allow_none=True)
    adoption = fields.Dict()
    social_media = fields.Dict()
    photos = fields.List(fields.Dict())
    distance = fields.Float()
    _links = fields.Dict()