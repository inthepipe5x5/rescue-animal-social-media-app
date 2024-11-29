import os
import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from sqlalchemy import desc, func
from sqlalchemy.dialects.postgresql import bulk_insert_mappings
from Project.core import db
from Project.services.petfinder import PetFinderAPI
from Project.models import Animal, AnimalCity, City
from Project.schemas.animals import AnimalRequestSchema, AnimalResponseSchema
from Project.services.data.pipeline import Pipeline


class PetFinderPipeline(Pipeline, PetFinderAPI):
    """
    PetFinder-specific pipeline subclass for managing animal and organization data.
    """

    ANIMAL_RESPONSE_SCHEMA = AnimalResponseSchema()
    ANIMAL_REQ_SCHEMA = AnimalRequestSchema()
    ANIMAL_MODEL = "Animal"

    CSV_COLUMN_HEADERS = {
        "animals": [],
        "orgs": [],
    }

    def __init__(cls):
        super.__init__()
        # dynamically update the CSV_COLUMN_headers from /mock_data sample files
        parsed_json_paths = [
            (
                parsed_json.replace("pf_", "").replace("_parsed.json", "s"),
                cls.get_relative_path_to_file(
                    parent_dir="/mock_data", target_file=parsed_json
                ),
            )
            for parsed_json in ["pf_animal_parsed.json", "pf_org_parsed.json"]
        ]
        for header_type, path in parsed_json_paths:
            with open(Path(path).relative_to(os.getcwd()), "r") as file:
                data = json.loads(file)
                cls.CSV_COLUMN_HEADERS.update(header_type, data.keys())

    def initial_animals_pipeline(self):
        self.run_pipeline()
        

    # override parent dynamic csv
    def create_nested_animal_location_csv_dir(
        self,
        location_dict: dict[str, Any],
        data_type: str = "animals",
    ):
        location_dict = (
            location_dict
            if location_dict
            else {
                "city": self.starting_city.get("name", "Toronto"),
                "state": self.starting_city.get("region_code", "ON"),
                "country": self.starting_city.get("country_code", "CA"),
            }
        )

        return self.create_dynamic_csv(
            constraints=location_dict,
            file_type=data_type,
        )


    def animal_pipeline(self):
        """Create a pipeline to scrape /animals data
        """
        
        all_cities_by_population = City.all_saved_cities(sort_by_pop=True)

        for city in all_cities_by_population:
            if city.name.casefold != self.starting_city.casefold:
                location = (
                    city.geolocation
                    if "geolocation" in city
                    else f"{city.name},{city.region_code}"
                )
                params = {
                    "location": location,
                    "limit": 100,
                    "sort": "distance",
                    "distance": 500,
                }
                endpoint = "animals"
                request_url = urljoin(self.BASE_API_URL, endpoint)
                animals = self._get_request(
                    request_url=request_url, endpoint=endpoint, params=params
                )
                if animals.status_code == 200:
                    for animal in animals:
                        new_animal = AnimalCity.create_from_combined_dict(
                            combined_animal_location_dict=animal
                        )