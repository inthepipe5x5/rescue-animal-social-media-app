from typing import Any, Dict, Optional

from sqlalchemy import desc
from sqlalchemy.orm import class_mapper
from Project.schemas.geography import CitySchema
from Project.services import geodb
from Project.core.extensions import db
from Project.utils.utils import TwoCharString
from Project.core.types import GeoLocationType

class City(db.Model):
    """
    Table to store cities data.

    This model represents a city in the database, storing various attributes such as
    name, country, geographical location, and population. It is designed to work with
    data scraped from geodbcities API and provides a structured way to store and
    retrieve city information.

    Attributes:
        id (int): Unique identifier for the city.
        type (str): Type of the location (e.g., "CITY").
        name (str): Name of the city.
        country (str): Name of the country where the city is located.
        country_code (str): Two-character uppercase country code.
        state (str): State, territory, or province of the city.
        region_code (str): Two-character uppercase state/region code.
        geolocation (str): Geographical coordinates in the format "(latitude,longitude)".
        population (int): Population of the city.
    """

    __tablename__ = "cities"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    country_code = db.Column(db.String(2), nullable=False)
    state = db.Column(db.String(100))
    region_code = db.Column(db.String(2))
    geolocation = db.Column(db.String(50))
    population = db.Column(db.Integer)
    postal_code = db.Column(db.String(10))

    # Foreign relationships
    # FK to Animals

    animals = db.relationship("Animal", back_populates="city")

    def __init__(
        self,
        id: Optional[int],
        type: Optional[str],
        name: Optional[str],
        country: Optional[str],
        country_code: Optional[TwoCharString],
        region_name: Optional[str],
        region_code: Optional[TwoCharString],
        geolocation: Optional[GeoLocationType],
        latitude: Optional[float],
        longitude: Optional[float],
        population: Optional[int],
        postal_code: Optional[str],
    ):
        self.id = id
        self.type = type
        self.name = name.strip(" ").lower()
        self.country = country
        self.country_code = country_code.upper()
        self.region_name = region_name
        self.region_code = region_code.upper()
        self.geolocation: str = f"({latitude},{longitude})"
        self.population = population
        self.postal_code = postal_code

        # Validate the instance using CitySchema
        city_schema = CitySchema()
        errors = city_schema.validate(self.__dict__)
        if errors:
            raise ValueError(f"Invalid city data: {errors}")

    @staticmethod
    def find(city_name: str, **kwargs) -> bool:
        """
        Check if a city exists in the database.

        Args:
            city_name (str): Name of the city (required).
            kwargs (dict): Optional filter criteria (e.g., state, country, country_code).

        Returns:
            city (object) if found else None
        """
        # Filter the kwargs to match City model columns
        valid_columns = {col.name for col in City.__table__.columns}
        filters = {key: value for key, value in kwargs.items() if key in valid_columns}

        # Build the query
        query = db.session.query(City).filter(
            City.name.casefold() == city_name.casefold()
        )
        for key, value in filters.items():
            query = query.filter(getattr(City, key).casefold() == value.casefold())

        return query.one_or_none()

    @classmethod
    def check_city_exists(cls, city_name: str, **kwargs) -> bool:
        """
        Check if a city exists in the database.

        Args:
            city_name (str): Name of the city (required).
            kwargs (dict): Optional filter criteria (e.g., state, country, country_code).

        Returns:
            bool: True if the city exists, False otherwise.
        """
        return bool(cls.find(city_name=city_name, kwargs=kwargs))

    def to_dict(self):
        """Deserializes instance to a python dict


        Returns:
            dict: deserialized db columns
        """
        return {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }

    @staticmethod
    def all_cities_by_pop():
        """Returns all cities in the database by population

        Returns:
            _type_: _description_
        """
        return db.session.query(City).order_by(desc(City.population)).all()

    @staticmethod
    def validate_city_data(city_data: Dict[str, Any], **kwargs: Any) -> None:

        city_name = city_data.get("city") or city_data.get("name")
        # Query the database for the city
        pre_existing_city = City.check_city_exists(
            city_name=city_name,
            state=city_data.get("state"),
            country=city_data.get("country"),
        )

        if pre_existing_city:
            pre_existing_city: Dict[str, Any] = {
                # "email": pre_existing_city.email,
                # "phone": pre_existing_city.phone,
                # "address": {
                "city": pre_existing_city.name,
                "country": pre_existing_city.country,
                "state": pre_existing_city.state,
                "postal_code": pre_existing_city.postal_code,
                # },
            }
        # check if city
        if not geodb.compare_location_dicts(city_data, pre_existing_city):
            new_city = City(**city_data)
            db.session.add(new_city)
            db.session.commit()

