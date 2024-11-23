# Custom Validator
from marshmallow_sqlalchemy.fields import String


class TwoCharString(String):
    def _deserialize(self, value, attr, data, **kwargs):
        if len(value) != 2:
            raise ValueError("Must be a 2-character string")
        return value