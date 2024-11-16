from sqlalchemy import Column, Integer, String, Boolean, JSON

# from sqlalchemy.dialects.postgresql import JSONB

from Project.schemas.common import SchemaDbModel
from Project.schemas.animals import AnimalSchema


# subclass for Animals
class Animal(SchemaDbModel, schema=AnimalSchema):
    """
    Represents an animal in the database.

    This model stores all information about an animal, including its attributes,
    matching the structure of an returned from PetFinder /animalsAPI response.
    """

    __tablename__ = "animals"
    api_list_key = "animals"

    id = Column(String(50), primary_key=True)


if __name__ == "__main__":
    pass
