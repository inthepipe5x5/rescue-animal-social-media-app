from requests import HTTPError
from http.client import HTTPException
from urllib.parse import urljoin
from core import (
    current_user,
    default_error_details as error_details,
    NEXT_ANIMAL_URLS_KEY,
    LOCATION_SESSION_KEY,
    USER_LOCATION_KEY,
    default_session_keys,
    DEFAULT_LOCATION,
)
from services import pf as api, AnimalTypes
from schemas import AnimalReqParams
from app import app


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


# Custom Validator
class TwoCharString(str):
    def __new__(cls, value):
        if len(value) != 2:
            raise ValueError("Must be a 2-character string")
        return super().__new__(cls, value)


# Handle Error
def handle_error(e):
    """Handle both HTTP exceptions and other exceptions."""
    error_code = e.code if isinstance(e, (HTTPException, HTTPError)) else 500

    error_info = error_details.get(
        error_code,
        {
            "error_title": f"{error_code} Error",
            "error_subtitle": "An unexpected error occurred.",
            "error_message": "We're sorry, but something went wrong on our end. Please try again later.",
            "redirect_url": "/",
            "redirect_text": "Back to Home",
        },
    )

    return (
        render_template(
            "error_page.html",
            error_title=error_info["error_title"],
            error_subtitle=error_info["error_subtitle"],
            error_message=error_info["error_message"],
            redirect_url=request.args.get("redirect_url", error_info["redirect_url"]),
            redirect_text=request.args.get(
                "redirect_text", error_info["redirect_text"]
            ),
        ),
        error_code,
    )


# session methods ##################################################################################################################
def get_anon_user() -> dict:
    """Grabs anon user data stored in the session

    Raises:
        TypeError: _description_

    Returns:
        _type_: _description_
    """
    animal_types = session.get(CURR_ANIMALS_KEY) or default_session_keys.get(
        CURR_ANIMALS_KEY
    )
    current_location = session.get(USER_LOCATION_KEY) or default_session_keys.get(
        USER_LOCATION_KEY
    )
    # Anonymous user, pull location from session
    get_anon_location()


def get_anon_location() -> dict:
    with app.app_context():
        # Anonymous user, pull location from session
        return {
            "city": app.session.get("city"),
            "state": app.session.get("state"),
            "postal_code": app.session.get("postal_code"),
            "geolocation": app.session.get("geolocation"),
        } or default_session_keys.get(DEFAULT_LOCATION)


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
    with app.app_context():

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
            app.session[LOCATION_SESSION_KEY] = location_dict
            # update current location
            app.session.setdefault(LOCATION_SESSION_KEY, current_location)

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
    default_animal_status = "adoptable,found"

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
    if not species_list:
        species_list = (
            current_user.animal_types
            if active_authenticated_user()
            else session.get("ANIMAL_TYPES", ["dog"])
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
