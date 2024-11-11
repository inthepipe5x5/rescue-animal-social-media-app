from flask import flash
import os
from .constants import *
from .methods import *
from .types import *
from .extensions import (
    db,
    ma,
    login_manager,
    login_required,
    SessionInterface,
    SessionMixin,
    load_user,
    login_user,
    logout_user,
)
from ..models import UserLocation, UserTravelPreferences
from ..services import pf as api
from ..app import app
from ..utils import Parse

from api import register_bp
# Register blueprints
app = register_bp(app)

def do_login(user):
    """Log in user."""
    with app.app_context():
        # add user.id to session
        app.session[CURR_USER_KEY] = user.id
        app.session["CURR_USER"] = (
            user.serialize()
        )  # needs to be JSON serializable to be saved
        app.g.user = user.serialize()  # auto calls the Model.serialize()
        # update the other global variables
        # add_animal_types_to_g(session, g)
        # add_location_to_g(session, g)
        # update_global_variables(session, g)
        # app.session.update(USER_LOCATION_KEY, user.location.city_state_country_str())
        # app.session.update("ANIMAL_TYPES", user.animal_types)
        load_session()
        app.logger.info(
            f"do_login({user.username}) successful. session[CURR_USER]=",
            app.session["CURR_USER"],
        )
        # use flask-login's login user function
        login_user(user, remember=True)


def do_logout():
    """Logout user."""

    app.session.pop(CURR_USER_KEY, default=None)
    app.session.pop("CURR_USER", default=None)

    # return stored values to default
    # reset animal types
    app.session.pop(
        CURR_ANIMALS_KEY, default=os.environ.get("ANIMAL_TYPES", ["dog"])
    )  # reset CURR_LOCATION
    app.session.pop(
        USER_LOCATION_KEY, default=os.environ.get(USER_LOCATION_KEY, "Toronto, ON")
    )
    # app.logger.info(f"do_logout successful. session[CURR_USER]=", (session["CURR_USER"] if "CURR_USER" in session  else None))
    app.g.pop("user", None)
    # clear session and create new session
    app.session.clear()
    app.session.new = True

    # flask-login's logout user => will clean up the cookie if it exists
    logout_user()


def load_session():
    """Update the app.session with user values if user else populates with default values"""

    # populate with default for anon-users for new sessions
    if not active_authenticated_user() and app.session.new == True:
        return init_default_session()
    else:
        user_id = (
            current_user.id
            if (
                active_authenticated_user()
                and (app.session.new == True or app.session.modified == True)
            )
            else None
        )
        user_session_data = current_user._get_current_object().serialize()
        if user_session_data:
            # update app.session with state_country, animal_types, curr_location, distance
            app.session.update(user_session_data)

def init_default_session():
    """Initialize the app.session with default values"""
    with app.app_context():
        # clear app.session
        do_logout()
        # populate with default_session_keys
        for key, value in default_session_keys.items():
            app.session.setdefault(key, value)
        app.session["STATE_COUNTRY"] = f"{default_session_keys['location']}"
        app.session.new = True
        app.session.modified = True


# TODO: I can move this to the User ORM class in models.py and call from `current_user._get_current_object`` instead
# Helper function to get the location or default location
def get_location(no_geocode=False):
    """
    Retrieves location from user data or app.session or defaults to a preset location.
    Args:
        user_location (UserLocation): Location object related to the current user.
    Returns:
        str: A geolocation string or postal code based on the user's or default location.
    """
    # If the user is authenticated and active
    if active_authenticated_user():
        user = load_user(user_id=current_user.id)
        user_location = (
            user.location
            if user and user.location
            else db.app.session.query(UserLocation)
            .filter_by(user_id=current_user.id)
            .first()
        )

        # update db if user_location found but not linked to user
        if user_location and not user.location:
            user.location = user_location
            # save to db
            db.app.session.add(user)
            db.app.session.commit()

        if no_geocode:
            #     return (
            #     f"{user_location.city}, {user_location.state} {user_location.postal_code}"
            #     if user_location.city
            #     and user_location.state
            #     and user_location.postal_code
            #     else user_location.get_location_info()
            # )  # return city/state/str eg. for UI rendering purposes

            return api.get_next_location(
                user_location.serialize()
            )  # return city/state/str eg. for UI rendering purposes
        else:
            return (
                user_location.geolocation or user_location.get_location_info()
            )  # returns first truthy location column
    # handle anon user
    else:
        if no_geocode:
            location_dict = {}
            for key, default_location_value in default_session_keys.get(
                DEFAULT_LOCATION
            ).items():
                location_dict[key] = app.session.get(key) or default_location_value

            return api.get_next_location(location_dict)


def create_init_params(req_type="animal"):
    """
    Dynamically creates and returns a dictionary of initialization parameters for
    API calls based on the user's authentication state, preferences, and location.

    Args:
        req_type (str): The req_type of object to fetch ('animal' or 'org'). Default is 'animal'.

    Returns:
        dict: A dictionary of API query parameters including req_type, page, location, distance, and limit.
    """

    # Common app.session values or default ones
    current_page_count = (
        app.session.get("CURRENT_DISCOVER_ANIMALS_PAGE", 1)
        if req_type.lower() in ["animal", "animals"]
        else app.session.get("CURRENT_DISCOVER_ORGS_PAGE", 1)
    )
    distance_pref = app.session.get(
        "DISTANCE_PREF", default_session_keys["DISTANCE_PREF"]
    )

    # If the user is authenticated and active
    if active_authenticated_user():
        user = current_user._get_current_object().serialize()
        user_location = user.get("location") or user.location.serialize()

        # Get user-specific data or defaults
        species = user.animal_types
        if not species:
            flash("Please select what type of animals you're looking for")
            return app.redirect(app.url_for("/users/animal_preferences"))

        # prettify the animal types for the API to accept it
        species = Parse.prettify_animal_types(animal_types=species, fuzzy_match=True)

        # get location str from serialized location dict
        location_str = api.get_next_location(user_location)

        distance_pref = (
            user.distance_pref
            if user and user.distance_pref
            else (
                UserTravelPreferences._get_distance_filter_param(
                    user_id=current_user.id
                )
                or 100
            )
        )

        status = (
            user.get("rescue_interaction_type")
            or get_rescue_action_mapped_to_animal_status()
        )
    else:
        # Non-authenticated user, default settings
        species = app.session.get(CURR_ANIMALS_KEY) or default_session_keys.get(
            CURR_ANIMALS_KEY, "dog"
        )
        # prettify the animal types for the API to accept it
        species = Parse.prettify_animal_types(animal_types=species, fuzzy_match=True)
        location_str = app.session.get(USER_LOCATION_KEY) or os.environ.get(
            USER_LOCATION_KEY, "43.6429,-79.3889"
        )
        distance_pref = app.session.get("DISTANCE_PREF", 100)

    # Set limit based on species length (more species = more results per page)
    species_len = len(species) or 1
    limit = (15 if 0 < species_len < 8 else 10) * species_len

    # create status param => "adoptable, adopted, found" PetFinderAPI Accepts multiple values (default: adoptable)
    # Return parameters for animal search
    if req_type.lower() in ("animal", "animals"):
        output_params = {
            "type": species,
            "page": current_page_count,
            "location": location_str,
            "distance": distance_pref,
            "limit": limit,
            "sort": "distance",  # Sort results by distance
        }
        # add status query param only if truthy (ie. user wants to adopt)
        if status:
            output_params["status"] = status

        return output_params

    # Return parameters for organization search
    elif req_type.lower() in ("org", "orgs", "organization", "organizations"):
        output_params = {
            "type": species,
            "page": current_page_count,
            "location": location_str,
            "state": str(
                user_location.state
                if user_location
                else default_session_keys.get(DEFAULT_LOCATION).get("state", "ON")
            ),  # Fallback state to ON
            "country": str(
                user_location.country
                if user_location
                else default_session_keys.get(DEFAULT_LOCATION).get("country", "CA")
            ),  # Fallback country to CA
            "distance": distance_pref,
            "limit": limit,
            "sort": "distance",  # Sort results by distance
        }

        return output_params


if __name__ == "__main__":
    pass
