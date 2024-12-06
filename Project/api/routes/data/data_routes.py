from flask import (
    Blueprint,
    json,
    request,
    jsonify,
    session,
    flash,
    render_template,
    url_for,
)
import os
import pycountry
from flask_login import login_required
from Project.core.constants import CURR_ANIMALS_KEY, default_session_dict
from Project.core.extensions import db
from Project.api.routes.data.methods import seed_animal_info
from Project.core.methods import active_authenticated_user, current_user
from Project.models import UserAnimalPreferences

data_bp = Blueprint("data", __name__, template_folder="templates", url_prefix="/data")


# @data_bp.before_request
@data_bp.route("/animal_types", methods=["GET", "POST"])
def update_animal_types():
    if request.method == "POST":
        selected_types = request.form.getlist("animal_types")
        # Update the current user's animal types via the current_user proxy
        if active_authenticated_user():
            # Update the current user's animal types
            current_user.animal_types = selected_types
            try:
                db.session.commit()
                flash("Animal types updated successfully", "success")
            except Exception as e:
                db.session.rollback()
                flash("An error occurred while updating animal types", "error")
                current_app.logger.error(
                    f"Error updating animal_types for user {current_user.id} @ {request.url} => {str(e)}"
                )
                return (
                    jsonify({"error": "An error occurred while updating animal types"}),
                    500,
                )
        else:
            # Limit anonymous users to just one selection
            selected_type = selected_types[0] if selected_types else "dog"
            session["ANIMAL_TYPES"] = [selected_type]
            flash("Animal type updated successfully", "success")

        return jsonify({"animal_types": current_user.animal_types}), 201

    # handle get requests
    else:
        animal_types = (
            current_user.animal_types
            if active_authenticated_user()
            else default_session_dict.get(CURR_ANIMALS_KEY, ["dog"])
        )
        return jsonify({"animal_types": animal_types}), 200


@data_bp.route("/animal_types/meta", methods=["GET"])
def get_animal_types_meta():
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


@data_bp.route("/<country>/state", methods=["GET"])
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
@data_bp.route("/prefs/<animal_type>", methods=["GET"])
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


@data_bp.route("/loading")
def loading_route():
    """Route to render loading

    Returns:
        renders view with skeleton loading cards and then directs after 5 seconds
    """
    redirect_url = request.args.get("redirect_url") or url_for("home")
    redirect_interval = request.args.get("redirect_interval") or 5000

    return render_template(
        url_for("templates", filename="loading_view.html"),
        redirect_url=redirect_url,
        redirect_interval=redirect_interval,
    )
