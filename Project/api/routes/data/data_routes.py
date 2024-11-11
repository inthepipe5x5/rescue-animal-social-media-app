from flask import Blueprint, json, redirect, request, jsonify, session, flash
import os
import pycountry

from core import login_required, active_authenticated_user, current_user
from services import pf as api
from models import UserAnimalPreferences

data_bp = Blueprint("data", __name__, template_folder="templates", url_prefix="/data")


@data_bp.before_request
def seed_animal_info():
    """Make API call for animal types information and save it to session and environment."""
    API_ANIMAL_TYPES_KEY = "API_ANIMAL_TYPES"

    # Retrieve type list from session or environment
    type_list = (
        session.get(API_ANIMAL_TYPES_KEY)
        or json.loads(os.environ.get(API_ANIMAL_TYPES_KEY, "[]"))
        or None
    )

    if (
        not type_list
        and API_ANIMAL_TYPES_KEY not in session
        and API_ANIMAL_TYPES_KEY not in os.environ
    ):
        # make API call if
        type_list = api.seed_animal_types()

        # Store the type_list in session and environment
        session[API_ANIMAL_TYPES_KEY] = type_list
        os.environ[API_ANIMAL_TYPES_KEY] = json.dumps(type_list)


@data_bp.route("/data/animal_types", methods=["GET"])
def get_animal_types():
    """Endpoint to retrieve animal types from session or os.environ."""
    types_session_key = "API_ANIMAL_TYPES"
    # handle if request is to refresh saved animal_types
    if request.args and ("api", "API", "seed", "SEED", "new", "NEW") in request.args:
        type_list = seed_animal_info()
    # handle if
    else:
        type_list = session.get(types_session_key) or json.loads(
            os.environ.get(types_session_key, "[]")
        )

    return jsonify({"types": type_list})


@data_bp.route("/data/<country>/state", methods=["GET"])
def get_state(country):
    """
    Data route to return list of states/provinces/subdivisions based on the country.

    Args:
        country (str): The name or alpha-2 code of the country.

    Returns:
        flask.Response: A JSON response containing the list of subdivisions and a message.
    """
    if not country:
        return jsonify({"results": [], "message": "Invalid country: empty input"})

    try:
        if len(country) == 2 and country.isalpha():
            # If it's a 2-letter code, try to find the country by its alpha-2 code
            found_country = pycountry.countries.get(alpha_2=country.upper())
        else:
            # Otherwise, search by name
            found_country = pycountry.countries.search_fuzzy(country)[0]
    except LookupError:
        return jsonify({"results": [], "message": f"No country found: {country}"})

    # Get all subdivisions for the found country
    subdivisions = list(pycountry.subdivisions.get(country_code=found_country.alpha_2))

    # Format the results
    # slice sub.code with [3::] to return 'NS'instead of 'CA-NS'
    formatted_subdivisions = [
        {
            "name": sub.name,
            "code": sub.code[3::].upper(),
            "type": sub.type,
            "parent_code": sub.parent_code,
        }
        for sub in subdivisions
    ]

    subdivision_msg = (
        f"No subdivisions found for {found_country.name}"
        if not subdivisions
        else f"{len(subdivisions)} subdivision(s) found for {found_country.name}"
    )

    return jsonify(
        {
            "results": formatted_subdivisions,
            "message": subdivision_msg,
            "country": {
                "name": found_country.name,
                "alpha_2": found_country.alpha_2,
                "alpha_3": found_country.alpha_3,
            },
        }
    )


@login_required
@data_bp.route("/data/prefs/<animal_type>", methods=["GET"])
def animal_pref_data(animal_type):
    if animal_type[-1].lower() == "s":
        species = animal_type.lower()[:-1]
    else:
        species = animal_type.lower()

    if active_authenticated_user():
        user_id = current_user.id
    else:
        # user_id = 18  # user: 99299@99299.com
        return jsonify(
            {"results": [], "success_flag": False, "message": "No user logged in"}
        )
    user_animal_prefs = UserAnimalPreferences.get_user_animal_pref_obj(
        u_id=user_id, animal_type=species
    )
    if user_animal_prefs:
        message = "User animal preferences retrieved successfully."
        category = "success"
    else:
        message = "No animal preferences found."
        category = "error"
    flash(message=message, category=category)
    return jsonify(user_animal_prefs)
