from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, JSON
from sqlalchemy.exc import IntegrityError

# from sqlalchemy.dialects.postgresql import JSONB


# from Project.schemas.common import SchemaDbModel
from Project.schemas.animals import AnimalSchema
from Project.models.geography import City, CitySchema
from Project.core.extensions import db
from Project.services.petfinder.petfinder_types import AnimalType


# subclass for Animals
# class Animal(SchemaDbModel, schema=AnimalSchema):
#     """
#     Represents an animal in the database.

#     This model stores all information about an animal, including its attributes,
#     matching the structure of an returned from PetFinder /animalsAPI response.
#     """

#     __tablename__ = "animals"
#     api_list_key = "animals"

#     id = Column(String(50), primary_key=True)


class Animal(db.Model):
    __tablename__ = "animals"

    id = db.Column(db.String(50), primary_key=True)
    type = db.Column(db.Enum(AnimalType), nullable=False)
    name = db.Column(db.String(100))
    breeds = db.Column(db.String(100))
    size = db.Column(db.String(20))
    gender = db.Column(db.String(20))
    age = db.Column(db.String(20))
    color = db.Column(db.String(50))
    coat = db.Column(db.String(20))
    status = db.Column(db.String(20))
    organization_id = db.Column(db.String(50))
    description = db.Column(db.Text)

    # Attributes
    spayed_neutered = db.Column(db.Boolean, default=False)
    house_trained = db.Column(db.Boolean, default=False)
    declawed = db.Column(db.Boolean, default=False)
    special_needs = db.Column(db.Boolean, default=False)
    shots_current = db.Column(db.Boolean, default=False)

    # Foreign relationships

    # Add a foreign key to reference the City model
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"))
    city_associations = db.relationship("AnimalCity", back_populates="animal")


class AnimalCity(db.Model):
    __tablename__ = "animal_city"

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.String(50), db.ForeignKey("animals.id"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=False)
    date_associated = db.Column(db.DateTime, default=datetime.now)

    # Define unique constraint to prevent duplicate associations
    __table_args__ = (db.UniqueConstraint("animal_id", "city_id"),)

    # Relationships
    animal = db.relationship("Animal", back_populates="city_associations")
    city = db.relationship("City", back_populates="animal_associations")

    def __init__(self, animal_id, city_id):
        self.animal_id = animal_id
        self.city_id = city_id

    @classmethod
    def create_from_combined_dict(cls, combined_animal_location_dict):
        if not combined_animal_location_dict:
            return None

        # Extract location data
        if "contact" in combined_animal_location_dict:
            location = combined_animal_location_dict.get("contact", {}).get("address", {})

        # Create or get City
        city_schema = CitySchema()
        city_data = {
            "name": location.get("city"),
            "state": location.get("state"),
            "country": location.get("country"),
            "postal_code": location.get("postal_code", None),
        }
        city = City.query.filter_by(
            name=city_data["name"], country=city_data["country"]
        ).first()
        if not city:
            city = city_schema.load(city_data)
            db.session.add(city)
            db.session.flush()  # This assigns an ID to the city if it's new

        # Create or get Animal
        animal_schema = AnimalSchema()
        animal_data = combined_animal_location_dict.copy()
        animal_data.pop(
            "contact", None
        )  # Remove contact info as it's handled separately
        animal = Animal.query.get(animal_data.get("id"))
        if not animal:
            animal = animal_schema.load(animal_data)
            db.session.add(animal)
            db.session.flush()

        # Create AnimalCity association
        animal_city = cls(animal_id=animal.id, city_id=city.id)
        db.session.add(animal_city)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            # Handle the case where the association already exists
            return None

        return animal_city

    @staticmethod
    def check_city_animals_exist(
        self, city_name: str, state: str, country: str, animal_id: int = None
    ) -> bool:
        """
        Check if animals exist for a given city, optionally filtering by animal ID.

        Args:
            city_name (str): Name of the city.
            state (str): State or province of the city.
            country (str): Country of the city.
            animal_id (int, optional): Specific animal ID to check for. Defaults to None.

        Returns:
            bool: True if matching animals exist, False otherwise.
        """
        # Start with a query joining Animal and City tables
        query = db.session.query(Animal).join(City)

        # Apply filters for city name, state, and country
        query = query.filter(
            City.name == city_name,
            City.state == state,
            City.country == country,
        )

        # If an animal_id is provided, add it to the filter
        if animal_id is not None:
            query = query.filter(Animal.id == animal_id)

        # Count the number of matching records
        count = query.count()

        # Return True if any matching records exist, False otherwise
        return count > 0


if __name__ == "__main__":
    pass
