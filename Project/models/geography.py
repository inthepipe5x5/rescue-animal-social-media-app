from typing import Any, Dict, List, Optional, Union

from sqlalchemy import desc
from sqlalchemy.orm import class_mapper, Query
from Project.models.common import MetaDataMixin, attach_listeners

# from Project.schemas.geography import CitySchema
from Project.services import geodb
from Project.core.extensions import db
from Project.utils.utils import TwoCharString
from Project.core.types import GeoLocationType


class City(db.Model, MetaDataMixin):
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
    country_name = db.Column(db.String(100), nullable=False)
    country_code = db.Column(db.String(2), nullable=False)
    region_name = db.Column(db.String(100), nullable=False)
    region_code = db.Column(db.String(2), nullable=False)
    geolocation = db.Column(db.String(50))
    population = db.Column(db.Integer)
    postal_code = db.Column(db.String(10))

    # Foreign relationships
    # FK to Animals
    animals = db.relationship(
        "Animal",
        secondary="animal_city",
        back_populates="cities",
        lazy="dynamic",
        uselist=True,
    )
    # animal_associations = db.relationship("AnimalCity", back_populates="city")

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
        self.geolocation: str = (
            geolocation
            if geolocation
            else f"({latitude},{longitude})" if (latitude and longitude) else None
        )
        self.population = population
        self.postal_code = postal_code

        # # Validate the instance using CitySchema
        # city_schema = CitySchema()
        # errors = city_schema.validate(self.__dict__)
        # if errors:
        #     raise ValueError(f"Invalid city data: {errors}")

    @staticmethod
    def find(city_name: str, return_all: bool = False, **kwargs) -> bool:
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

        return query.one_or_none() if not return_all else query.all()

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

    @property
    def to_dict(self):
        """Deserializes instance to a python dict


        Returns:
            dict: deserialized db columns
        """
        return {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }

    # properties to make the db column keys easier to map to petfinder service
    @property
    def state(self):
        return self.region_code

    @property
    def country(self):
        return self.country_code

    @property
    def postcode(self):
        return self.postal_code

    @staticmethod
    def all_saved_cities(
        as_query_obj: bool = False, sort_by_pop: bool = False
    ) -> Union[Query, Dict[tuple, Any]]:
        # base query
        query = City.query

        # Apply sorting if needed
        if sort_by_pop:
            query = query.order_by(desc(City.population))

        # Execute the query
        results = query.all()

        # Return as requested format
        if as_query_obj:
            return set(results)  # or list(results) if you prefer a list of objects
        else:
            return {
                (city.name, city.region_name, city.country_name): city
                for city in results
            }

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


# Call this function after all models are defined
attach_listeners()
