# Custom Validator
class TwoCharString(str):
    def __new__(cls, value):
        if len(value) != 2:
            raise ValueError("Must be a 2-character string")
        return super().__new__(cls, value)

