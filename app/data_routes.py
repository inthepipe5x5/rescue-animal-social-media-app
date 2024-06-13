from flask import Blueprint, render_template, g, request, session, jsonify

from helper import get_anon_preference, get_user_preference
from .PetFinderAPI import pf_api

data_bp = Blueprint('data', __name__, template_folder='templates', url_prefix='/data')


@data_bp.route("/data/animals", methods=["GET", "POST"])
def data():
    """TEST ROUTE TO USE PETPY API

    Args:
        type (STR): string of either 'animal', 'animals', 'org', 'orgs' that determine the type of PetFinder API call being made

    Returns:
        _type_: _description_
    """
    if g.user:
        country = get_user_preference(key="country")
        state = get_user_preference(key="state")
    else:
        country = get_anon_preference(key="country")
        state = get_anon_preference(key="state")

    location = country + "," + state
    print(country)
    results = pf_api.petpy_api.animals(
        location=location, sort="distance"
    )  # (**pf_api.default_options_obj)
    print([(org.name, org.adoption.policy) for org in results.organizations])
    # return jsonify(results)
    return render_template("results.html", results=results)


@data_bp.route("/data/orgs", methods=["GET", "POST"])
def orgs_data():
    """TEST ROUTE TO GET ORGS DATA

    Args:
        type (STR): string of either 'animal', 'animals', 'org', 'orgs' that determine the type of PetFinder API call being made

    Returns:
        _type_: _description_
    """
    if g.user:
        country = get_user_preference(key="country")
        state = get_user_preference(key="state")
    else:
        country = get_anon_preference(key="country")
        state = get_anon_preference(key="state")

    results = pf_api.petpy_api.organizations(
        country=country, state=state, sort="distance"
    )  # (**pf_api.default_options_obj)
    print([(org.name, org.adoption.policy) for org in results.organizations])
    # return jsonify(results)
    return render_template("results.html", results=results)


# Route to set & get API data in Flask Session
@data_bp.route("/data/session", methods=["GET", "POST"])
def update_data_session():
    if request.method == "GET":
        if "api_data" in session:
            del session["api_data"]
            return jsonify(session["api_data"])
        return jsonify({})  # Return empty JSON if no data in session

    if request.method == "POST":
        api_data = request.args.get("api_data")
        if api_data:
            session["api_data"] = pf_api.parse_api_animals_data(api_data=api_data)
        else:
            return ValueError("No api data received")
