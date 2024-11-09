from marshmallow import Marshmallow, Schema, fields, validate
from flask_sqlalchemy import SQLAlchemy

ma = Marshmallow()
db = SQLAlchemy()

# Database models
class Animal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
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

class AnimalAttributes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey('animal.id'))
    spayed_neutered = db.Column(db.Boolean)
    house_trained = db.Column(db.Boolean)
    declawed = db.Column(db.Boolean)
    special_needs = db.Column(db.Boolean)
    shots_current = db.Column(db.Boolean)

# Response schemas
class AnimalAttributesSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = AnimalAttributes

class AnimalSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Animal
        include_fk = True
    
    attributes = fields.Nested(AnimalAttributesSchema)
    photos = fields.List(fields.Dict())
    videos = fields.List(fields.Dict())
    tags = fields.List(fields.Str())
    contact = fields.Dict()
    _links = fields.Dict()

class AnimalListResponseSchema(Schema):
    animals = fields.List(fields.Nested(AnimalSchema))
    pagination = fields.Dict()

