from flask import current_app
from flask_login import current_user
from requests import HTTPError
from http.client import HTTPException
from urllib.parse import urljoin
import os

from Project.core.constants import (
    NEXT_ANIMAL_URLS_KEY,
    LOCATION_SESSION_KEY,
    USER_LOCATION_KEY,
    default_session_dict,
    DEFAULT_LOCATION,
    CURR_USER_KEY,
    CURR_ANIMALS_KEY,
    default_error_details,
)
from Project.core.extensions import db
from flask_login import login_user, logout_user
from Project.services import pf as api
from Project.services.petfinder.petfinder_types import AnimalTypes, AnimalReqParams
from Project.utils import Parse
from Project.services import pf as api
from Project.models import UserLocation, UserTravelPreferences


def do_login(user):
    """Log in user."""
    with current_app.app_context():
        # add user.id to session
        current_app.session[CURR_USER_KEY] = user.id
        current_app.session["CURR_USER"] = (
            user.serialize()
        )  # needs to be JSON serializable to be saved
        current_app.g.user = user.serialize()  # auto calls the Model.serialize()
        # update the other global variables
        # add_animal_types_to_g(session, g)
        # add_location_to_g(session, g)
        # update_global_variables(session, g)
        # current_app.session.update(USER_LOCATION_KEY, user.location.city_state_country_str())
        # current_app.session.update("ANIMAL_TYPES", user.animal_types)
        load_session()
        current_app.logger.info(
            f"do_login({user.username}) successful. session[CURR_USER]=",
            current_app.session["CURR_USER"],
        )
        # use flask-login's login user function
        login_user(user, remember=True)


def do_logout():
    """Logout user."""

    current_app.session.pop(CURR_USER_KEY, default=None)
    current_app.session.pop("CURR_USER", default=None)

    # return stored values to default
    # reset animal types
    current_app.session.pop(
        CURR_ANIMALS_KEY, default=os.environ.get("ANIMAL_TYPES", ["dog"])
    )  # reset CURR_LOCATION
    current_app.session.pop(
        USER_LOCATION_KEY, default=os.environ.get(USER_LOCATION_KEY, "Toronto, ON")
    )
    # current_app.logger.info(f"do_logout successful. session[CURR_USER]=", (session["CURR_USER"] if "CURR_USER" in session  else None))
    current_app.g.pop("user", None)
    # clear session and create new session
    current_app.session.clear()
    current_app.session.new = True

    # flask-login's logout user => will clean up the cookie if it exists
    logout_user()


def load_session():
    """Update the current_app.session with user values if user else populates with default values"""

    # populate with default for anon-users for new sessions
    if not active_authenticated_user() and current_app.session.new == True:
        return init_default_session()
    else:
        user_id = (
            current_user.id
            if (
                active_authenticated_user()
                and (
                    current_app.session.new == True
                    or current_app.session.modified == True
                )
            )
            else None
        )
        user_session_data = current_user._get_current_object().serialize()
        if user_session_data:
            # update current_app.session with state_country, animal_types, curr_location, distance
            current_app.session.update(user_session_data)


def init_default_session():
    """Initialize the current_app.session with default values"""
    with current_app.app_context():
        # clear current_app.session
        do_logout()
        # populate with default_session_dict
        for key, value in default_session_dict.items():
            current_app.session.setdefault(key, value)
        current_app.session["STATE_COUNTRY"] = f"{default_session_dict['location']}"
        current_app.session.new = True
        current_app.session.modified = True


# TODO: I can move this to the User ORM class in models.py and call from `current_user._get_current_object`` instead
# Helper function to get the location or default location
def get_location(no_geocode=False):
    """
    Retrieves location from user data or current_app.session or defaults to a preset location.
    Args:
        user_location (UserLocation): Location object related to the current user.
    Returns:
        str: A geolocation string or postal code based on the user's or default location.
    """
    # If the user is authenticated and active
    if active_authenticated_user():
        user = current_user._get_current_object()
        user_location = (
            user.location
            if user and user.location
            else db.current_app.session.query(UserLocation)
            .filter_by(user_id=current_user.id)
            .first()
        )

        # update db if user_location found but not linked to user
        if user_location and not user.location:
            user.location = user_location
            # save to db
            db.current_app.session.add(user)
            db.current_app.session.commit()

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
            for key, default_location_value in default_session_dict.get(
                DEFAULT_LOCATION
            ).items():
                location_dict[key] = (
                    current_app.session.get(key) or default_location_value
                )

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
    with current_app.app_context():
        # Common current_app.session values or default ones
        current_page_count = (
            current_app.session.get("CURRENT_DISCOVER_ANIMALS_PAGE", 1)
            if req_type.lower() in ["animal", "animals"]
            else current_app.session.get("CURRENT_DISCOVER_ORGS_PAGE", 1)
        )
        distance_pref = current_app.session.get(
            "DISTANCE_PREF", default_session_dict["DISTANCE_PREF"]
        )

        # If the user is authenticated and active
        if active_authenticated_user():
            user = current_user._get_current_object().serialize()
            user_location = user.get("location") or user.location.serialize()

            # Get user-specific data or defaults
            species = user.animal_types
            if not species:
                current_app.flash(
                    "Please select what type of animals you're looking for"
                )
                return current_app.redirect(
                    current_app.url_for("/users/animal_preferences")
                )

            # prettify the animal types for the API to accept it
            species = Parse.prettify_animal_types(
                animal_types=species, fuzzy_match=True
            )

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
            species = current_app.session.get(
                CURR_ANIMALS_KEY
            ) or default_session_dict.get(CURR_ANIMALS_KEY, "dog")
            # prettify the animal types for the API to accept it
            species = Parse.prettify_animal_types(
                animal_types=species, fuzzy_match=True
            )
            location_str = current_app.session.get(USER_LOCATION_KEY) or os.environ.get(
                USER_LOCATION_KEY, "43.6429,-79.3889"
            )
            distance_pref = current_app.session.get("DISTANCE_PREF", 100)

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
                    else default_session_dict.get(DEFAULT_LOCATION).get("state", "ON")
                ),  # Fallback state to ON
                "country": str(
                    user_location.country
                    if user_location
                    else default_session_dict.get(DEFAULT_LOCATION).get("country", "CA")
                ),  # Fallback country to CA
                "distance": distance_pref,
                "limit": limit,
                "sort": "distance",  # Sort results by distance
            }

            return output_params


def active_authenticated_user():
    """
    Util function to return True if `current_user` object from Flask-Login is truthy for both attributes:
        -current_user.is_active == True
        -current_user.is_authenticated == True
    """
    if (
        current_user
        and current_user.is_authenticated == True
        and current_user.is_active == True
        and bool(current_user.id)
    ):
        return True
    else:
        return False


# Handle Error
def handle_error(e):
    """
    Handle both HTTP exceptions and other exceptions by mapping them to a dictionary
    containing error details.

    Parameters:
    e (Exception): The exception object to handle.

    Returns:
    dict: A dictionary containing error details.
    """
    error_code = None
    error_info = {}

    # Check if the error is an HTTPException or HTTPError
    if isinstance(e, (HTTPException, HTTPError)):
        # Extract the status code from the HTTP exception
        if isinstance(e, HTTPException):
            error_code = e.code
        elif isinstance(e, HTTPError):
            error_code = e.response.status_code
    else:
        # For general exceptions, use a default error code (500)
        error_code = 500

    # Check if the error is a custom error with specific keys
    if hasattr(e, 'to_dict') and callable(e.to_dict):
        error_info = e.to_dict()
    elif hasattr(e, '__dict__') and set(default_error_details.keys()).issubset(set(e.__dict__.keys())):
        error_info = {
            key: e.__dict__.get(key, default_error_details.get(error_code, {}).get(key, ''))
            for key in default_error_details.get(error_code, {}).keys()
        }
    else:
        # Use the error code to find the mapped dict within default_error_details
        error_info = default_error_details.get(
            error_code,
            {
                "error_title": f"{error_code} Error",
                "error_subtitle": "An unexpected error occurred.",
                "error_message": "We're sorry, but something went wrong on our end. Please try again later.",
                "redirect_url": "/",
                "redirect_text": "Back to Home",
            },
        )

    return error_info


# session methods ##################################################################################################################
def get_anon_user() -> dict:
    """Grabs anon user data stored in the session

    Raises:
        TypeError: _description_

    Returns:
        _type_: _description_
    """
    with current_app.app_context():
        animal_types = current_app.session.get(
            CURR_ANIMALS_KEY
        ) or default_session_dict.get(CURR_ANIMALS_KEY)
        current_location = current_app.session.get(
            USER_LOCATION_KEY
        ) or default_session_dict.get(USER_LOCATION_KEY)
        # Anonymous user, pull location from session
        get_anon_location()


def get_anon_location() -> dict:
    with current_app.app_context():
        # Anonymous user, pull location from session
        return {
            "city": current_app.session.get("city"),
            "state": current_app.session.get("state"),
            "postal_code": current_app.session.get("postal_code"),
            "geolocation": current_app.session.get("geolocation"),
        } or default_session_dict.get(DEFAULT_LOCATION)


def create_next_animal_url(
    animal_types: AnimalTypes,
    params: AnimalReqParams,
    next_url_dict: dict = {},
    endpoint="animals",
) -> dict:

    next_urls = next_url_dict(NEXT_ANIMAL_URLS_KEY)
    if not next_urls and params:
        for animal_type in animal_types:
            {animal_type: urljoin(f"{api.BASE_API_URL}/{endpoint}", params)}

    return next_urls


def save_location_to_session(location_dict):
    """Function to save location to session as a dict

    Args:
        location_dict (dict): dict of location values to use

    Returns:
        location_dict: dict of location values to use
    """
    with current_app.app_context():

        if not location_dict:
            raise TypeError(
                f"Expected location_dict:<dict>: {location_dict} => passed into {__name__}"
            )
        else:
            current_location = (
                location_dict.get(LOCATION_SESSION_KEY, None)
                if LOCATION_SESSION_KEY in location_dict
                else api.get_next_location(location_dict=location_dict)
            )
            location_dict.setdefault(USER_LOCATION_KEY, current_location)
            # update session
            current_app.session[LOCATION_SESSION_KEY] = location_dict
            # update current location
            current_app.session.setdefault(LOCATION_SESSION_KEY, current_location)

            return location_dict


# Helper function to retrieve PetFinder API status query param based on rescue actions
def get_rescue_action_mapped_to_animal_status():
    """
    Fetches the appropriate PetFinder API status query parameter based on the user's rescue action type.

    Args:
        user (User): Current user object with a 'rescue_action_type' attribute.

    Returns:
        str: Status query parameter value for the PetFinder API.
    """
    # Default status to return when user is interested in adoption or fostering
    from Project.core import default_animal_status

    # Check if user and user.rescue_action_type exist, and retrieve the list
    if active_authenticated_user() and current_user.rescue_action_type:
        rescue_actions = set(current_user.rescue_action_type)

        # If the current_user only wants to volunteer and/or donate, return None (no status needed)
        if rescue_actions.issubset({"volunteering", "donation"}):
            return None

        # Otherwise, return the default status (-adopted, adoptable, found)
        return default_animal_status

    # If no current_user or no rescue_action_type is provided, return the default status
    return default_animal_status


# Helper function to retrieve user preferences for animals
def get_user_animal_preferences(species_list=None):
    """
    Fetches user preferences for each species or returns an empty dictionary.
    Args:
        species_list (list): List of species to query preferences for.
    Returns:
        dict: Dictionary of user preferences keyed by species type.
              {'dog': { 'preference_name': 'preference_data', ... }, ...}
    """
    with current_app.app_context():
        if not species_list:
            species_list = (
                current_user.animal_types
                if active_authenticated_user()
                else current_app.session.get("ANIMAL_TYPES", ["dog"])
            )

        # Get user preferences or set prefs to None if user is not authenticated
        prefs = {
            key: value
            for key, value in (
                current_user._get_current_object().animal_prefs
                if active_authenticated_user() and current_user.user_animal_preferences
                else {animal_type: None for animal_type in species_list}
            ).items()
            if key.lower() in species_list
        }

        # handle bad keys
        # API requires 'color' but returns key 'colors'
        for species_pref in prefs:
            if "color" in prefs[species_pref].keys():
                prefs[species_pref]["colors"] = prefs[species_pref]["color"]
                del prefs[species_pref]["color"]

        return prefs
