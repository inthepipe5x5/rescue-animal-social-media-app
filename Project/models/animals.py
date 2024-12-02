from datetime import datetime
import os
from typing import Union
from urllib.parse import urljoin

from sqlalchemy import NUMERIC
from sqlalchemy.event import listens_for
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import class_mapper
from sqlalchemy.dialects.postgresql import JSONB

# from sqlalchemy.dialects.postgresql import JSONB


# from Project.schemas.common import SchemaDbModel
from Project.models.common import MetaDataMixin, attach_listeners
from Project.schemas.animals import AnimalResponseSchema
from Project.models.geography import City
from Project.schemas.geography import CitySchema
from Project.core.extensions import db
from Project.services.petfinder.petfinder_types import AnimalType


# subclass for Animals
# class Animal(SchemaDbModel, schema=AnimalResponseSchema):
#     """
#     Represents an animal in the database.

#     This model stores all information about an animal, including its attributes,
#     matching the structure of an returned from PetFinder /animalsAPI response.
#     """

#     __tablename__ = "animals"
#     api_list_key = "animals"

#     id = Column(String(50), primary_key=True)


class Animal(db.Model, MetaDataMixin):
    __tablename__ = "animals"

    id = db.Column(db.String(50), primary_key=True)
    type = db.Column(db.Enum(AnimalType), nullable=False)
    name = db.Column(db.String(100))
    breeds = db.Column(db.String(100))
    size = db.Column(db.String(20))
    gender = db.Column(db.String(20))
    age = db.Column(db.String(20))
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

    # Environment
    children = db.Column(db.Boolean, default=False)
    dogs = db.Column(db.Boolean, default=False)
    cats = db.Column(db.Boolean, default=False)

    # social media, contact info and media links
    photos = db.Column(JSONB)
    videos = db.Column(JSONB)
    # dates
    published_at = db.Column(db.DateTime)

    # Relationships
    # Relationship to AnimalCity
    animal_city = db.relationship("AnimalCity", back_populates="animal")
    # Cities indirectly through AnimalCity
    cities = db.relationship(
        "City",
        secondary="animal_city",
        back_populates="animals",
        overlaps="animal_city",
    )
    # org
    organization_id = db.Column(db.String, db.ForeignKey("rescueOrg.id"))
    organization = db.relationship("Organization", back_populates="animals")

    @property
    def self_href(self) -> str:
        """
        The `self_href` property generates a URL based on the base URL, provider, and object ID.
        :return: The `self_href` property is returning a URL that is constructed by combining the base URL
        obtained from the `base_url` dictionary with the partial URL generated using the object's table name
        and id. The `urljoin` function is used to combine these two parts into a complete URL, which is then
        returned by the property.
        """
        base_url = self.base_url.get(
            self.provider if self.provider else "petfinder",
            os.environ.get("PETFINDER_API_URL"),
        )
        partial = f"{self.__tablename__}/{self.id}"
        return urljoin(base=base_url, url=partial, allow_fragments=True)

    @property
    def type_href(self) -> str:
        """
        The `type_href` property generates a URL for retrieving information about a specific type of pet
        from a pet adoption API.
        :return: The `type_href` property is returning a URL that is constructed by combining the base URL
        obtained from the `base_url` attribute, and a partial URL formed by appending "types/" followed by
        the value of the `type` attribute. The `urljoin` function is used to combine these two parts and
        return the final URL.
        """
        base_url = self.base_url.get(
            self.provider if self.provider else "petfinder",
            os.environ.get("PETFINDER_API_URL"),
        )
        partial = f"types/{self.type}"
        return urljoin(base=base_url, url=partial, allow_fragments=True)

    @property
    def organization_href(self) -> str:
        """
        The `organization_href` function generates a URL for accessing information about a specific
        organization based on the provided organization ID.
        :return: The `organization_href` property is being returned, which is a URL constructed by joining
        the base URL obtained from the `base_url` dictionary with the partial URL
        "organizations/{self.organization_id}". The `organization_id` is an attribute of the object. The
        final URL is created using the `urljoin` function with the base URL and the partial URL, and it
        allows fragments in the URL.
        """
        base_url = self.base_url.get(
            self.provider if self.provider else "petfinder",
            os.environ.get("PETFINDER_API_URL"),
        )
        partial = f"organizations/{self.organization_id}"
        return urljoin(base=base_url, url=partial, allow_fragments=True)


def set_provider(mapper, connection, target):
    if not target.provider:
        target.provider = "petfinder"


class AnimalCity(db.Model, MetaDataMixin):
    __tablename__ = "animal_city"

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.String(50), db.ForeignKey("animals.id"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=False)
    distance = db.Column(
        NUMERIC(10, 4), default=None
    )  # distance returned by PetFinder API

    # Define unique constraint to prevent duplicate associations
    __table_args__ = (db.UniqueConstraint("animal_id", "city_id"),)

    # Relationships back to the `City` and `Animal` models
    city = db.relationship(
        "City", back_populates="animal_city", overlaps="animals,cities" #to silence SA warning
    )
    animal = db.relationship(
        "Animal", back_populates="animal_city", overlaps="animals,cities" #to silence SA warning
    )

    def __init__(self, animal_id, city_id, distance=None):
        self.animal_id = animal_id
        self.city_id = city_id
        self.distance = distance

    @classmethod
    def create_from_combined_dict(
        cls, combined_animal_location_dict: dict[str, Union[bool, str, int, dict, list]]
    ):
        if not combined_animal_location_dict:
            return None

        # Extract location data
        location = combined_animal_location_dict.get("contact", {}).get("address", {})
        if not location:
            return None

        # Create or get City
        city_schema = CitySchema()
        city_data = {
            "name": location.get("city"),
            "state": location.get("state"),
            "country": location.get("country"),
            "postal_code": location.get("postal_code"),
        }

        city = City.query.filter_by(
            name=city_data["name"],
            state=city_data["state"],
            country=city_data["country"],
        ).first()

        if not city:
            try:
                city = city_schema.load(city_data)
                db.session.add(city)
                db.session.flush()  # Ensures the city ID is available
            except Exception as e:
                db.session.rollback()
                raise ValueError(f"Failed to create city: {e}")

        # Create or get Animal
        animal_schema = AnimalResponseSchema()
        animal_data = {
            key: value
            for key, value in combined_animal_location_dict.items()
            if key != "contact"
        }
        animal = Animal.query.get(animal_data.get("id"))

        if not animal:
            try:
                animal = animal_schema.load(animal_data)
                db.session.add(animal)
                db.session.flush()  # Ensures the animal ID is available
            except Exception as e:
                db.session.rollback()
                raise ValueError(f"Failed to create animal: {e}")

        # Create AnimalCity association
        animal_city = cls(
            animal_id=animal.id, city_id=city.id, distance=location.get("distance")
        )
        try:
            db.session.add(animal_city)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            # Handle duplicate association gracefully
            animal_city = cls.query.filter_by(
                animal_id=animal.id, city_id=city.id
            ).first()

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


# Call this function after all models are defined
attach_listeners()


if __name__ == "__main__":
    pass
