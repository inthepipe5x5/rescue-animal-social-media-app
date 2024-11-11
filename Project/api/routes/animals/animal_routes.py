from flask import Blueprint, json, redirect, request, session, url_for, jsonify
import pycountry
from urllib.parse import urljoin
from time import sleep
from core import (
    login_required,
    API_ANIMAL_TYPES_KEY,
    get_location,
    default_session_keys,
)
import os
from dotenv import load_dotenv
from data import seed_animal_info
from utils import Parse

from ....services import pf as api

load_dotenv()

animals_bp = Blueprint(
    "animals", __name__, template_folder="templates", url_prefix="/animals"
)


@animals_bp.route("/discover/animals/<animal_type>")
def discover_specific_animal_type(animal_type):

    types_list = session.get(API_ANIMAL_TYPES_KEY) or json.loads(
        os.environ.get(API_ANIMAL_TYPES_KEY, "[]")
    )

    # Validate animal_type
    if not types_list:
        # Make request to seed animal_types
        seed_animal_info()
        # Retry request to route
        return redirect(
            url_for("discover_specific_animal_type", animal_type=animal_type)
        )

    prettified_animal_type = Parse.prettify_animal_types(animal_type)

    if (animal_type, prettified_animal_type) not in types_list:
        return redirect(
            url_for(
                "custom_error",
                error_subtitle="Invalid Animal Type",
                error_title="Something went wrong...",
                error_message=f"Woops, we can't find that kind of animal to rescue...yet! {api.animal_emojis}",
            )
        )

    try:
        params = {
            "type": prettified_animal_type,
            "location": get_location(),
        }

        response = api.request_with_retry(
            endpoint="animals",
            request_url=urljoin(api.BASE_API_URL, "animals"),
            params=params,
        )

        data = api.log_and_raise_for_status(response) if response else None

        return jsonify({"results": data})
    except Exception as e:
        animals_bp.logger.error(f"{request.url} error: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred."}), 500


@animals_bp.route("/test/animals")
def test_animals():
    """Endpoint to retrieve data from PetFinder /animals route"""
    response = api.request_with_retry(
        request_url=urljoin(api.BASE_API_URL, "animals"),
        params={},
        endpoint="animals",
        max_retries=3,
    )
    data = response.json() or []
    return jsonify({"response": data})


@animals_bp.route("/test/animals/locations")
def test_location_animals():
    """TEST ROUTE TO TEST DIFFERENT COMBINATIONS OF PARAMS ACCEPTED BY PETFINDER API LOCATION PARAMS"""

    def fetch_data(location_str):
        params = {"location": location_str}
        response = api.request_with_retry(
            request_url=urljoin(api.BASE_API_URL, "animals"),
            params=params,
            endpoint="animals",
        )

        data = api.log_and_raise_for_status(response) if response else None
        return data, response.status_code if response else None

    location_dict = session.get("location", {}) or default_session_keys.get(
        "DEFAULT_LOCATION"
    )
    location_combinations = api.generate_location_combinations(location_dict)

    successful_combinations = []
    unsuccessful_combinations = []
    try:
        for key, value in location_combinations.items():
            sleep(3)
            data, status_code = fetch_data(value)
            if status_code in [200, 201] and data:
                successful_combinations.append({key: value})
            else:
                unsuccessful_combinations.append({key: value})

        return jsonify(
            {
                "successful_combinations": successful_combinations,
                "unsuccessful_combinations": unsuccessful_combinations,
            }
        )

    except Exception as e:
        animals_bp.logger.error(f"{request.url} error: {e}", exc_info=1)
        if "successful_combinations" in locals():
            successful_combinations = locals().get("successful_combinations", None)
            unsuccessful_combinations = locals().get("unsuccessful_combinations", None)
        return jsonify(
            {
                "successful_combinations": (
                    successful_combinations if successful_combinations else []
                ),
                "unsuccessful_combinations": (
                    unsuccessful_combinations if unsuccessful_combinations else []
                ),
            }
        )
