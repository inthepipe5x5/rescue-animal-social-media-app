from flask import Blueprint, request, redirect, url_for, jsonify
from dotenv import load_dotenv
from urllib.parse import urljoin
import requests
from time import sleep
from typing import List, Callable, Any
from Project.models.geography import City, CitySchema
from Project.services.data import seed_initial_cities
from Project.services.petfinder.PetFinderAPI import pf as api
from Project.services.petfinder.petfinder_types import RequestedContent, AnimalReqParams
from Project.core import db
from Project.schemas.animals import Animal, AnimalListResponseSchema, AnimalSchema
from models import Animal

import logging
from logging.config import dictConfig
from Project.config import Config

pf_bp = Blueprint(
    "pf", __name__, url_prefix="/pf", url_defaults=url_for("return_animals")
)
load_dotenv()


@pf_bp.route("/animals", methods=["POST"])
def return_animals():
    """Route to return scraped PetFinder /animals data"""

    # TODO:
    # params = request.body.get("params")
    # if params:
    #     db.session.query(Animal).filter()

    animals = db.session.query(Animal).limit(20)
    return jsonify(animals)


@pf_bp.route("/animals/scrape", methods=["POST"])
def scrape_animals():
    """Route to scrape /animals"""

    params = request.body.get("params")
    AnimalReqParams.loads(params)

    min_params = [
        ("limit", 100),
        ("location", "43.651070,-79.347015"),
        ("request_url", urljoin(api.BASE_API_URL, "animals", params)),
    ]
    # set min params
    if min_params not in params:
        for param in min_params:
            params.setdefault(param[0], param[1])

    response = api._get_animals(params=params)
    if response:
        response.raise_for_status()
        data: RequestedContent = response.json()
        validated_data = Animal(schema=AnimalSchema)
        Animal.db_bulk_insert_mapping(session=db.session)

        next_url = Animal.get_next_url(data.get("pagination", {}))
        params.setdefault("request_url", next_url)
        sleep(20)
        request.post(url_for("scrape_animals", _external=True), params=params)
        return jsonify({"data": validated_data})


# Configure logging
logging.config.dictConfig(Config.get_logger_config())
logger = logging.getLogger(__name__)


def validate_saved_cities(
    db: Any,
    check_db_func: Callable[[str, Any], bool],
    http_request_func: Callable[[str], Any],
    save_to_db_func: Callable[[Any, Any], None],
) -> None:
    """
    Validate cities saved in db, making HTTP requests and saving updated data to the database if incomplete data found.

    :param cities: List of city names to process
    :param db: Database object (Flask SQLAlchemy object)
    :param check_db_func: Function to check if an entry exists in the database
    :param http_request_func: Function to make HTTP requests
    :param save_to_db_func: Function to save data to the database
    """
    query_all_cities = db.session.query(City).all()
    query_all_cities_dicts = (
        [city.to_dict() for city in query_all_cities]
        if query_all_cities
        else seed_initial_cities()
    )

    for city in query_all_cities_dicts:
        try:
            # Check if the city result has falsy column values
            get_updated_data_flag = any(bool(val) for val in city.values())

            if get_updated_data_flag:
                logger.info(
                    f"City {city} requires updating..making HTTP request to GEODB cities API."
                )
                # Make HTTP request
                data = http_request_func(city)
                validated_data = CitySchema.loads(data)
                updated_city = City(**validated_data)
                db.session.add()
                db.commit()

            # Save data to database
            save_to_db_func(data, db)

            logger.info(f"Successfully processed and saved data for {city}")

            # Add a small delay to avoid overwhelming the server
            sleep(2)

        except Exception as e:
            logger.error(f"Error processing {city}: {str(e)}")

    logger.info("Finished processing all cities")
