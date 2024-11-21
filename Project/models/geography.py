from typing import Optional
from marshmallow import pre_load
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import desc
from sqlalchemy.orm import class_mapper
from Project.services import geodb
from Project.core.extensions import db
from Project.core.types import GeoLocationType
from Project.utils.utils import TwoCharString


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
    def check_city_exists(city_name: str, state: str, country: str) -> bool:
        query = (
            db.session.query(City)
            .filter(City.name.casefold() == city_name.casefold())
            .one_or_none()
        )

        return True if query else False

    def dump(self):
        return geodb.process_city_data(city_data=self.to_dict())

    def to_dict(self):
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
    

class CitySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = City
        load_instance = True
        include_relationships = True
        include_fk = True

    country_code = TwoCharString()
    region_code = TwoCharString()
    geolocation = GeoLocationType()

    @pre_load
    def process_data(self, data: dict, **kwargs):
        return geodb.process_city_data(city_data=data)
