from typing import Any
from sqlalchemy import desc, func
from sqlalchemy.dialects.postgresql import bulk_insert_mappings
from Project.core import db
from Project.services.petfinder import PetFinderAPI
from Project.core.constants import default_session_keys, DEFAULT_LOCATION
from Project.models import Animal, AnimalCity, City
from Project.schemas.animals import AnimalRequestSchema, AnimalResponseSchema
from Project.services.data.pipeline import Pipeline

starting_city = default_session_keys.get(DEFAULT_LOCATION)["city"]


class PetFinderPipeline(Pipeline, PetFinderAPI):
    """
    PetFinder-specific pipeline subclass for managing animal and organization data.
    """

    ANIMAL_RESPONSE_SCHEMA = AnimalResponseSchema()
    ANIMAL_REQ_SCHEMA = AnimalRequestSchema()
    ANIMAL_MODEL = "Animal"
    
    CSV_COLUMN_HEADERS = {
        "animals": [],
        "orgs": ["id", "name", "state", "country", "website"],
    }
    def __init__():
        super.__init__()

    def initial_animals_pipeline():
        all_cities_by_population = City.all_saved_cities(sort_by_pop=True)

        for city in all_cities_by_population:
            if city.name.casefold != starting_city.casefold:
                geolocation = (
                    city.geolocation
                    if "geolocation" in city
                    else f"{city.name},{city.region_code}"
                )
                params = {
                    "location": geolocation,
                    "limit": 100,
                    "sort": "distance",
                    "distance": 500,
                }
                animals = pf._get_request(endpoint="animals", params=params)
                if animals.status_code == 200:
                    for animal in animals:
                        new_animal = AnimalCity.create_from_combined_dict(combined_animal_location_dict=animal)
                        bulk_insert_mapping
    # override parent dynamic csv
    def create_nested_animal_location_csv_dir(
        self,
        location_dict: dict[str, Any] = {
            "country": "CA",
            "state": "ON",
            "city": starting_city,
        },
        data_type: str = "animals",
    ):
        return self.create_dynamic_csv(
            constraints=location_dict,
            file_type=data_type,
        )
