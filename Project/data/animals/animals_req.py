from marshmallow import Schema, fields, validate
from flask_marshmallow import Marshmallow

ma = Marshmallow()

# Request parameter validation schema
class AnimalRequestSchema(Schema):
    type = fields.Str(validate=validate.OneOf(["dog", "cat", "rabbit", "small-furry", "horse", "bird", "scales-fins-other", "barnyard"]))
    breed = fields.List(fields.Str())
    size = fields.List(fields.Str(validate=validate.OneOf(["small", "medium", "large", "xlarge"])))
    gender = fields.List(fields.Str(validate=validate.OneOf(["male", "female", "unknown"])))
    age = fields.List(fields.Str(validate=validate.OneOf(["baby", "young", "adult", "senior"])))
    color = fields.Str()
    coat = fields.List(fields.Str(validate=validate.OneOf(["short", "medium", "long", "wire", "hairless", "curly"])))
    status = fields.List(fields.Str(validate=validate.OneOf(["adoptable", "adopted", "found"])))
    name = fields.Str()
    organization = fields.List(fields.Str())
    good_with_children = fields.Boolean()
    good_with_dogs = fields.Boolean()
    good_with_cats = fields.Boolean()
    house_trained = fields.Boolean()
    declawed = fields.Boolean()
    special_needs = fields.Boolean()
    location = fields.Str()
    distance = fields.Int(validate=validate.Range(min=1, max=500))
    before = fields.DateTime(format="iso")
    after = fields.DateTime(format="iso")
    sort = fields.Str(validate=validate.OneOf(["recent", "-recent", "distance", "-distance", "random"]))
    page = fields.Int(validate=validate.Range(min=1))
    limit = fields.Int(validate=validate.Range(min=1, max=100))
