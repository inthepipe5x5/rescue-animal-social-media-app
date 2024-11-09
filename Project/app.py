from flask import (  # type: ignore
    Flask,
    render_template,
    request,
    flash,
    redirect,
    session,
    g,
    url_for,
    jsonify,
    Blueprint,
    send_from_directory,
    abort,
)
from flask.sessions import (
    SessionInterface,
    SessionMixin,
    NullSession,
)
from flask_login import (
    LoginManager,
    login_required,
    login_user,
    logout_user,
    current_user,
)
from petpy import Petfinder
from sqlalchemy.exc import IntegrityError, NoResultFound  # type: ignore
from dotenv import load_dotenv  # type: ignore
import os
import pycountry
from time import sleep
import json
from urllib.parse import urljoin
import requests

# from functools import wraps #TODO: to protect certain API routes
from flask_bcrypt import Bcrypt
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import HTTPException
# from marshmallow import MarshMallow

from Project.data.users.models import (
    db,
    User,
    UserLocation,
    UserAnimalPreferences,
    UserTravelPreferences,
    UserFavorites,
)
from forms import (
    UserAddForm,
    LoginForm,
    UserEditForm,
    UserExperiencesForm,
    UserLocationForm,
    AnonExperiencesForm,
    SpecificAnimalPreferencesForm,
    HiddenForm,
    HiddenLocationForm,
    UserTravelForm,
)
from package.helper import (
    data_bp,
    get_anon_preference,
    get_user_preference,
    update_anon_preferences,
    update_user_preferences,
    update_global_variables,  # currently in helper.py
    add_user_to_g,
    add_location_to_g,
    add_animal_types_to_g,
)
from config import config, Config
from package.PetFinderAPI import PetFinderAPI
from package.parse import Parse
# import custom exceptions
from package.api_exceptions import (
    PetFinderResourceNotFoundError,
    PetFinderInvalidCredentialsError,
    PetFinderAccessDeniedError,
    PetFinderInvalidParametersError,
    PetFinderLocationError,
    PetFinderUnexpectedServerError,
)

# default session keys
CURR_USER_KEY = os.environ.get("CURR_USER_KEY", "curr_user")

# keys to use to store key app values in Flask Session
CURR_ANIMALS_KEY = "ANIMAL_TYPES"
DEFAULT_LOCATION = "DEFAULT_LOCATION"
DISTANCE_KEY = "DISTANCE_PREF"
RESULTS_PER_PAGE_KEY = "RESULTS_PER_PAGE"
VIEWED_CONTENT_KEY = "VIEWED_CONTENT_LIST"
USER_LOCATION_KEY = "CURR_LOCATION"
NEXT_ANIMAL_URLS_KEY = "NEXT_URLS"

load_dotenv()

default_session_keys = {
    USER_LOCATION_KEY: os.environ.get(USER_LOCATION_KEY, "43.6429,-79.3889"),
    CURR_ANIMALS_KEY: os.environ.get("ANIMAL_TYPES", ["dog"]),
    DEFAULT_LOCATION: {
        "geolocation": "43.6429,-79.3889",
        "state": "ON",
        "country": "CA",
        "postal_code": "m5j0b3",
        "city": "Toronto",
    },
    DISTANCE_KEY: 100,
    RESULTS_PER_PAGE_KEY: 6,  # default is 6 (so render 2 rows of 3 columns of cards)
    VIEWED_CONTENT_KEY: [],  # list of id of PetFinder API content seen by the user
}


def create_app():
    # create Flask app
    app = Flask(__name__)

    # create config instance
    app_config_instance = Config()

    # config Flask app
    flask_env_type = (
        os.environ.get("FLASK_ENV")
        if os.environ.get("FLASK_ENV") is not None
        else "default"
    )
    app_config_instance.config_app(app=app, obj=config[flask_env_type])

    # register blueprints
    app.register_blueprint(data_bp)

    # init default session values
    with app.app_context():
        app.session_interface.init_session(session)
    return app


# create Flask app
app = Flask(__name__)
# app.session_interface = CustomSessionInterface()

# create config instance
app_config_instance = Config()

# config Flask app
flask_env_type = (
    os.environ.get("FLASK_ENV")
    if os.environ.get("FLASK_ENV") is not None
    else "default"
)

app_config_instance.config_app(app=app, obj=config[flask_env_type])  # type: ignore
# app = create_app()
# config bcrypt
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Inject Custom Jinja filters Here
custom_filters_dict = {
    "format_kebob_case": Parse.format_kebob_case,
    "prettify_animal_types": Parse.prettify_animal_types,
}
for function_key, function in custom_filters_dict.items():
    app.jinja_env.filters[function_key] = function

# api instance of helper class
api = PetFinderAPI()


# # petpy instance
# petpy = Petfinder(key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET"))

# # set auth in petpy
# if not petpy._auth:
#     petpy._auth = os.environ.get("ACCESS_TOKEN", None)

##############################################################################
# SESSION FUNCTIONS

# class CustomSession(dict, SessionMixin):
#     """Custom Session Interface to handle session management by expanding beyond the basic dictionary functionality of Flask Session
#     Args:
#         dict (_type_): Python Dictionary
#         SessionMixin (_type_): Mixin from Flask Session that expands the default session object in Flask
#     """

#     def init_default_session():
#         """Initialize the session with default values"""
#         for key, value in default_session_keys.items():
#             session.setdefault(key, value)
#         session.new = True
#         session.modified = True

#     def init_session(self):
#         """Initialize the session with USER if user values else populates with default values"""

#         #populate with default for anon-users
#         if not active_authenticated_user():
#             return self.init_default_session()
#         else:
#             user_id=current_user.id
#             user_session_data = get_user_data(user_id=user_id)
#             if user_session_data:
#                 #update session with state_country, animal_types, curr_location, distance
#                 session.update(user_session_data)


#     def reset_session(self):
#         """Reset the session to default values"""
#         self.clear()
#         self.init_session()

# class CustomSessionInterface(SessionInterface):
#     def open_session(self, app, request):
#         session = CustomSession()
#         session.init_session()
#         app.logger.info(f"Session initialized - {session}")
#         return session

#     def reset_session(self, app, session):
#         session.reset_session()
#         app.logger.info(f"Session reset to default - {session}")

##############################################################################
# User signup/login/logout

# TODO: REMOVE LATER AS I'M USING THE SAME FUNCTION FROM FLASK-LOGIN INSTEAD
# def login_required(route_func):
#     @wraps(route_func)
#     def protected_route(*args, **kwargs):
#         if CURR_USER_KEY not in session:
#             # flash error
#             flash("Unauthorized", "danger")
#             # not authenticated, redirect to login and then requested url once authenticated
#             return redirect(url_for("login"), next=request.url)
#         # else the user is authenticated and should be allowed to proceed to the protected route
#         return route_func(*args, **kwargs)

#     return protected_route


# def require_api_key(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         api_key = request.headers.get("X-API-Key")
#         if api_key and api_key == os.environ.get("SECRET_KEY"):
#             return f(*args, **kwargs)
#         else:
#             abort(401)  # Unauthorized

#     return decorated_function


# user load function to load user session based on user_id
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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


def do_login(user):
    """Log in user."""
    # add user.id to session
    session[CURR_USER_KEY] = user.id
    session["CURR_USER"] = user.serialize()  # needs to be JSON serializable to be saved
    g.user = user.serialize()  # auto calls the Model.serialize()
    # update the other global variables
    # add_animal_types_to_g(session, g)
    # add_location_to_g(session, g)
    # update_global_variables(session, g)
    # session.update(USER_LOCATION_KEY, user.location.city_state_country_str())
    # session.update("ANIMAL_TYPES", user.animal_types)
    load_session()
    app.logger.info(
        f"do_login({user.username}) successful. Session[CURR_USER]=",
        session["CURR_USER"],
    )
    # use flask-login's login user function
    login_user(user, remember=True)


def do_logout():
    """Logout user."""

    session.pop(CURR_USER_KEY, default=None)
    session.pop("CURR_USER", default=None)

    # return stored values to default
    # reset animal types
    session.pop(
        CURR_ANIMALS_KEY, default=os.environ.get("ANIMAL_TYPES", ["dog"])
    )  # reset CURR_LOCATION
    session.pop(
        USER_LOCATION_KEY, default=os.environ.get(USER_LOCATION_KEY, "Toronto, ON")
    )
    # app.logger.info(f"do_logout successful. Session[CURR_USER]=", (session["CURR_USER"] if "CURR_USER" in session  else None))
    g.pop("user", None)
    # clear session and create new session
    session.clear()
    session.new = True

    # flask-login's logout user => will clean up the cookie if it exists
    logout_user()


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

    # Anonymous user, pull location from session
    return {
        "city": session.get("city"),
        "state": session.get("state"),
        "postal_code": session.get("postal_code"),
        "geolocation": session.get("geolocation"),
    } or default_session_keys.get(DEFAULT_LOCATION)


def get_next_animal_urls(animal_types, params, endpoint="animals",) -> dict:
        
    next_urls = session.get(
        NEXT_ANIMAL_URLS_KEY
    )
    if not next_urls and params:
        for animal_type in animal_types:
            {animal_type: urljoin(f"{api.BASE_API_URL}/{endpoint}", params) }    


    return next_urls

@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)

        if user:
            do_login(user)
            g.user = user
            session["CURR_USER"] = user.serialize()
            print(g.user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", "danger")

    return render_template("users/login.html", form=form)


@login_required
@app.route("/logout")
def logout():
    """Handle logout of user."""
    # remove user from session
    do_logout()
    # populate default session data in
    init_default_session()
    flash(f"Log out successful. Hope to see you again", "success")
    return redirect("/")


##############################################################################
# General user routes:


@app.route("/users")
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get("q")

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template("users/index.html", users=users)


@app.route("/users/<int:user_id>")
def show_user(user_id):
    user = User.query.get_or_404(user_id)
    user_location_form = UserLocationForm(obj=user.location)
    user_travel_form = UserTravelForm(obj=user.travel_preference)
    return render_template(
        "users/show.html",
        user=user,
        user_location_form=user_location_form,
        user_travel_form=user_travel_form,
    )


# Form route available to both anon and users but only user location is saved to db
@app.route("/users/location", methods=["GET", "POST"])
def update_user_location():
    app.logger.info(
        f"Request method: {request.method}, Current user.location: {current_user.location if (active_authenticated_user() and current_user.location) else 'No Saved Location'}"
    )
    try:
        if active_authenticated_user() and current_user.location:
            form = UserLocationForm(obj=current_user.location)
        else:
            form = UserLocationForm()

        if form.validate_on_submit():
            if current_user.location:
                location = current_user.location
                form.populate_obj(location)
                app.logger.info("Updating existing location")
            else:
                location = UserLocation(user_id=current_user.id)
                form.populate_obj(location)
                app.logger.info("Creating new location")

            if form.geolocation.data:
                coordinates = form.geolocation.data
                location.geolocation = UserLocation.format_geolocation(coordinates)
                app.logger.info(f"Setting geolocation: {location.geolocation}")

            location.city = location.city.lower() if location.city else None

            db.session.add(location)
            db.session.commit()

            app.logger.info(f"Location saved: {form.data}")
            flash("Location updated successfully!", "success")

            # update session logic
            location_dict = save_location_to_session(location_dict=location.serialize())
            if request.is_json:
                return jsonify({"location": location_dict})

            viewed_content = session.get("VIEWED_CONTENT_LIST", [])
            # load session
            load_session()
            # keep viewed content in session
            session["VIEWED_CONTENT_LIST"] = viewed_content

            return redirect(url_for("show_user", user_id=current_user.id))

        return render_template(
            "/users/form.html",
            form=form,
            form_title="Where are you located?",
            page_scripts=[
                url_for("static", filename="geolocation.js"),
                url_for("static", filename="setStateCountryInput.js"),
            ],
        )
    except Exception as e:
        app.logger.error(f"Error in update_user_location: {str(e)}")
        db.session.rollback()
        flash(
            "An error occurred while updating your location. Please try again.", "error"
        )


@login_required
@app.route("/users/travel", methods=["GET", "POST"])
def user_travel_preferences():
    travel_preferences = UserTravelPreferences.query.filter_by(
        user_id=current_user.id
    ).first()

    if not current_user.location:
        flash("Please set your location details first", "warning")
        return redirect(url_for("update_user_location"))

    if travel_preferences:
        form = UserTravelForm(obj=travel_preferences)
    else:
        form = UserTravelForm()

    if form.validate_on_submit():
        if not travel_preferences:
            travel_preferences = UserTravelPreferences(user_id=current_user.id)
        # update the sqlalchemy object
        form.populate_obj(travel_preferences)

        # save to db
        db.session.add(travel_preferences)
        db.session.commit()

        # update distance_pref stored in session
        session.modified = True
        new_distance_pref = form.data.get("distance_filter_preference", 100)
        session["DISTANCE_PREF"] = new_distance_pref

        # flash message to user for feedback
        flash("Travel preferences updated successfully!", "success")
        return redirect(url_for("show_user", user_id=current_user.id))

    return render_template(
        "/users/form.html",
        form=form,
        form_title="How far are you willing to travel?",
        page_scripts=[url_for("static", filename="setTravelPreference.js")],
    )


@login_required
@app.route("/users/favorite/<fav_type>", methods=["GET"])
def show_user_favorites(fav_type):
    """Add or toggle a favorite for the currently-logged-in user."""

    fav_type = "all" if not fav_type else fav_type.lower()

    user = (
        current_user
        if current_user.is_authenticated
        else session.get("CURR_USER", None)
    )
    if not user:
        flash("Access unauthorized.", "danger")
        return redirect(url_for("login"))

    try:
        if fav_type == "all":
            user_favorites = UserFavorites.get_favorites(user_id=user.id)

        # return fave orgs
        elif fav_type.lower() in (
            "orgs",
            "organizations",
            "organization",
            "rescue",
            "rescues",
        ):
            user_favorites = UserFavorites.get_orgs_favorites(user_id=user.id)

        # return fave animals if fave_type not specified
        # elif fav_type == 'animals':
        else:
            user_favorites = UserFavorites.get_animal_favorites(user_id=user.id)

        return jsonify(
            {
                "user_id": user.id,
                "action": fav_type,
                "results": user_favorites if user_favorites else [],
            }
        )

    except Exception as e:
        # db.session.rollback()
        return (
            jsonify(
                {
                    "error": "Error getting favorites @ show_user_favorites API route =>"
                    + str(e)
                }
            ),
            500,
        )


@login_required
@app.route("/users/favorite/<int:favorite_id>", methods=["POST"])
def user_favorite(favorite_id):
    """Add or toggle a favorite for the currently-logged-in user."""

    is_animal = request.args.get("is_animal", "true").lower() == "true"
    action = request.args.get("action", "toggle").lower()

    user = (
        current_user
        if current_user.is_authenticated
        else session.get("CURR_USER", None)
    )
    if not user:
        flash("Access unauthorized.", "danger")
        return redirect(url_for("login"))

    try:
        if action == "add":
            user.add_favorite(favorite_id=favorite_id, is_animal=is_animal)
            message = f"Added {'Animal' if is_animal else 'Rescue Org'} #{favorite_id} to favorites"
        elif action == "toggle":
            result = user.toggle_favorite(favorite_id=favorite_id, is_animal=is_animal)
            message = f"{'Added' if result else 'Removed'} {'Animal' if is_animal else 'Rescue Org'} #{favorite_id} {'to' if result else 'from'} favorites"
        else:
            return jsonify({"error": "Invalid action"}), 400

        flash(message)
        return jsonify(
            {
                "favorite_id": favorite_id,
                "action": action,
                "result": result if action == "toggle" else True,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/users/animal_types", methods=["GET", "POST"])
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
                app.logger.error(
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
            else default_session_keys.get(CURR_ANIMALS_KEY, ["dog"])
        )
        return jsonify({"animal_types": animal_types}), 200


def save_location_to_session(location_dict):
    """Function to save location to session as a dict

    Args:
        location_dict (dict): dict of location values to use

    Returns:
        location_dict: dict of location values to use
    """
    # key to use to store in session
    LOCATION_SESSION_KEY = "location"
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
        session[LOCATION_SESSION_KEY] = location_dict
        # update current location
        session.setdefault(LOCATION_SESSION_KEY, current_location)

        return location_dict


@login_required
@app.route("/users/profile", methods=["GET", "POST"])
def profile():
    """Update profile for current user."""
    # TODO write this to accept a dict of values to update on the current user
    if request.method == "POST" and request.body:
        pass

    if not active_authenticated_user():
        flash("Access unauthorized.", "danger")
        return redirect(url_for("login"))

    else:
        active_user = current_user._get_current_object()
        form = UserEditForm(obj=active_user)

        if form.validate_on_submit():
            if User.authenticate(form.username.data, form.password.data):
                form.populate_obj(active_user)
                db.session.add(active_user)
                db.session.commit()  # commit to db
                flash("Changes saved successfully", "success")  # show success to user
                return redirect(url_for("show_user", user_id=g.user.id))
            else:
                db.session.rollback()
                flash(
                    "You were unsuccessful, try again", "error"
                )  # show success to user
                return render_template("users/edit.html", form=form, user=active_user)

        return render_template("users/edit.html", form=form, user=active_user)


@app.route("/users/delete", methods=["POST"])
def delete_user():
    """Delete user."""

    if not active_authenticated_user() or "CURR_USER" not in session:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(session["CURR_USER"])
    db.session.commit()
    flash("Deleted current user successfully", "success")
    return redirect("/signup")


##############################################################################
IMAGE_FOLDER = os.path.join("static", "images", "graphics")


# TODO # FIX LATER
# @app.route("/static/images/graphics/<path:filename>")
# def serve_image(filename):
#     return send_from_directory(IMAGE_FOLDER, f"/{filename}")


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


# TODO: I can move this to the User ORM class in models.py and call from `current_user._get_current_object`` instead
# Helper function to get the location or default location
def get_location(no_geocode=False):
    """
    Retrieves location from user data or session or defaults to a preset location.
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
            else db.session.query(UserLocation)
            .filter_by(user_id=current_user.id)
            .first()
        )

        # update db if user_location found but not linked to user
        if user_location and not user.location:
            user.location = user_location
            # save to db
            db.session.add(user)
            db.session.commit()

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
                location_dict[key] = session.get(key) or default_location_value

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

    # Common session values or default ones
    current_page_count = (
        session.get("CURRENT_DISCOVER_ANIMALS_PAGE", 1)
        if req_type.lower() in ["animal", "animals"]
        else session.get("CURRENT_DISCOVER_ORGS_PAGE", 1)
    )
    distance_pref = session.get("DISTANCE_PREF", default_session_keys["DISTANCE_PREF"])

    # If the user is authenticated and active
    if active_authenticated_user():
        user = current_user._get_current_object().serialize()
        user_location = user.get("location") or user.location.serialize()

        # Get user-specific data or defaults
        species = user.animal_types
        if not species:
            flash("Please select what type of animals you're looking for")
            return redirect("")

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
        species = session.get(CURR_ANIMALS_KEY) or default_session_keys.get(
            CURR_ANIMALS_KEY, "dog"
        )
        # prettify the animal types for the API to accept it
        species = Parse.prettify_animal_types(animal_types=species, fuzzy_match=True)
        location_str = session.get(USER_LOCATION_KEY) or os.environ.get(
            USER_LOCATION_KEY, "43.6429,-79.3889"
        )
        distance_pref = session.get("DISTANCE_PREF", 100)

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


# helper function to combine location & animal_preference_filters
def create_user_preference_filters():
    filters = {}

    if not active_authenticated_user():
        # filter by default location only
        location_pref = {
            key: value
            for key, value in default_session_keys["DEFAULT_LOCATION"].items()
            if key in ["state", "country"]
        }
        # return only location prefs as filter functions
        return api.create_filter_conditions(preferences=location_pref)

    # handle real user
    else:
        user_prefs = get_user_animal_preferences(
            user_id=current_user.id, species_list=current_user.animal_types
        )
        user_location = (
            db.session.query(UserLocation)
            .filter(UserLocation.user_id == current_user.id)
            .first()
        )
        # Create location filters
        location_filters = api.create_filter_conditions(
            preferences={
                "state": user_location.city,
                "country": user_location.state,
            }
        )
        if user_prefs:
            # Loop through animal types and combine animal & location filters
            for animal_type, preferences in user_prefs.items():
                # Create animal preference filters
                animal_filter = api.create_filter_conditions(preferences=preferences)

                # # Combine animal and location filters without nesting under the same key
                # filters[animal_type] = {
                #     **animal_filter,  # Animal filters for the specific type
                #     **location_filters,  # Location filters (state, country)
                # }
        else:
            filters = location_filters

        return filters


@app.route("/discover/animals", methods=["GET"])
def discover_animals():
    """Route to fetch and display paginated animal data, with error handling and fallback UI in case of API downtime."""

    user = current_user._get_current_object() if active_authenticated_user() else None

    # Determine user location
    location_data = None

    # Get location from user's serialized data
    location_data = user.serialize().get("location") if user else get_anon_location()
    if not location_data:
        return redirect(url_for('form_users_location'))
    
    init_params = create_init_params(req_type="animals")
    animal_types = (
        request.args.get("animal_type")
        or init_params.get("type")
        or user.get("animal_types")
        or session.get("ANIMAL_TYPES", ["dog"])
    )
    target_count = int(
        request.args.get("limit") or session.get(RESULTS_PER_PAGE_KEY) or init_params.get("limit", 9)
    )  # Number of animals per page

    # Prepare exclude_ids for viewed or favorited animals
    user_favorites = user.get_all_favorites if user else []
    viewed_content = session.get("VIEWED_CONTENT_LIST", [])
    exclude_ids = set(viewed_content + user_favorites)

    # Flatten user preferences for API request
    flattened_animal_preferences = (
        api.preprocess_preferences(
            init_params=init_params.copy(),
            prefs_obj=get_user_animal_preferences(species_list=animal_types),
        )
        if user
        else {animal_type: None for animal_type in animal_types}
    )

    # Ensure animal_types is always a list
    animal_types = [animal_types] if isinstance(animal_types, str) else animal_types
    
    next_urls = get_next_animal_urls(animal_types=animal_types, endpoint='animals')

    render_content = []
    # try:

    while len(render_content) < target_count:
        session[NEXT_ANIMAL_URLS_KEY] = next_urls  # Save updated next URLs in session
        
        # Combine initial parameters with animal preferences and location if provided
        params = init_params.copy().update(flattened_animal_preferences) if flattened_animal_preferences else init_params.copy()
            
        # set params['location'] properly
        if location_data or isinstance(params.get("location"), (dict, object)):
            params["location"] = api.get_next_location(location_dict=location_data)

        for animal_type in animal_types:
            next_url = next_urls.get(animal_type) or urljoin(f"{api.BASE_API_URL}/animals", params)

            if not next_url:
                continue  # Skip this type if no next URL is available (exhausted)
            # Fetch data from the API using request_with_retry
            results = api.request_with_retry(
                endpoint="animals", request_url=next_url, params=params
            )
        
        if not results:
            raise PetFinderResourceNotFoundError()
            break  # Exit if generator returns no content

        # Filter and parse results
        filters = create_user_preference_filters()
        filtered_results, success_flag = api.filter_parse_animal_results(
            results, filter_prefs=filters
        )
        render_content.extend(filtered_results)

        # Add viewed content to session if successful
        if success_flag:
            session["VIEWED_CONTENT_LIST"] = list(
                set(
                    session.get("VIEWED_CONTENT_LIST", [])
                    + [result["id"] for result in filtered_results]
                )
            )
            break

    # No content message
    if len(render_content) == 0:
        flash(
            "No animals found matching your filters. Adjust filters or try again later!",
            "warning",
        )
        init_params = {"limit": target_count}

        # Attempt backup API call if no content
        try:
            backup_results = api._get_request(
                "animals", f"{api.BASE_API_URL}/animals", params=init_params
            )
            if not backup_results:
                return redirect(
                    url_for(
                        "custom_error",
                        error_title="PetFinder API Unavailable",
                        error_subtitle="We're sorry for the inconvenience.",
                        error_message="PetFinder's API is temporarily down. Please try again later.",
                    )
                )
            render_content = backup_results.get("animals", [])
        except Exception as api_error:
            app.logger.error(f"API Backup Call Failed: {api_error}")
            return redirect(
                url_for(
                    "custom_error",
                    error_title="PetFinder API Error",
                    error_subtitle="Unable to retrieve animals.",
                    error_message="Our system is currently experiencing issues connecting to PetFinder. Please try again later.",
                )
            )

    # except PetFinderAccessDeniedError as e:
    #         #wait attempt number of seconds in case of rate limiting
    #         sleep(int(attempt))
    #         #reset access token
    #         self._get_access_token()
    #         if attempt == max_retries:
    #             break
    #         else:
    #             continue
    #     except PetFinderInvalidParametersError as e:
    #         # Handle invalid parameters by removing problematic keys and retrying
    #         invalid_params = (
    #             e.invalid_params or []
    #         )  # Retrieve invalid params from error, if available
    #         for param in invalid_params:
    #             params.pop(param, None)  # Remove invalid key
    #         continue  # Retry request with modified parameters

    #     except PetFinderLocationError:
    #         # Handle location errors by cycling through alternative locations
    #         location_dict = params.get("location", {})
    #         while location_dict:
    #             next_location, location_dict = self.get_alternative_locations(
    #                 location_dict
    #             )

    #             if not next_location:
    #                 # All location alternatives have been exhausted; redirect user to enter location
    #                 return PetFinderLocationError(
    #                     error_title="Error determining location",
    #                     error_subtitle="Please set your location",
    #                     error_message=(
    #                         "Can't determine your location for local content. "
    #                         "Please enter your location or enable geolocation for more accurate results."
    #                     ),
    #                     redirect_url="/users/location",
    #                 ).error_info()

    #             # Update params with the new location and retry request
    #             params["location"] = next_location
    #             response = self._get_request(
    #                 endpoint,
    #                 request_url or f"{self.BASE_API_URL}/{endpoint}",
    #                 params=params,
    #             )
    #             self.log_and_raise_for_status(response)
    #             return response.json()  # Return if successful

    #     except RateLimitException:
    #         print("Rate limit reached. Retrying...")

    # # If max retries without success, raise a final error
    # raise Exception(f"Request to {endpoint} failed after {max_retries} retries.")



        # Respond with JSON for AJAX or render HTML
        if request.is_json:
            return jsonify(
                {"results": render_content, "success_flag": bool(render_content)}
            )

        return render_template("results.html", animals=render_content)

    # except Exception as e:
    #     app.logger.error(f"Error at endpoint {request.endpoint}: {e}")
    #     return redirect(
    #         url_for(
    #             "custom_error",
    #             error_title="Unexpected Error",
    #             error_subtitle="We ran into an issue!",
    #             error_message="Our system encountered an issue loading animals. Please try refreshing the page or come back later.",
    #         )
    #     )


# @app.route("/discover/animals", methods=["GET"])
# def discover_animals():
#     """Route to fetch and display paginated animal data, with error handling and fallback UI in case of API downtime."""

#     user = current_user._get_current_object() if active_authenticated_user() else None

#     # Determine user location
#     location_data = None
#     if user:
#         # Get location from user's serialized data
#         location_data = user.serialize().get("location")
#     else:
#         # Anonymous user, pull location from session
#         location_data = {
#             "city": session.get("city"),
#             "state": session.get("state"),
#             "postal_code": session.get("postal_code"),
#             "geolocation": session.get("geolocation"),
#         } or default_session_keys.get(DEFAULT_LOCATION)

#     init_params = create_init_params(req_type="animals")
#     animal_types = (
#         request.args.get("animal_type")
#         or init_params.get("type")
#         or user.get("animal_types")
#         or session.get("ANIMAL_TYPES", ["dog"])
#     )
#     target_count = int(
#         request.args.get("limit") or init_params.get("limit", 9)
#     )  # Number of animals per page

#     # Prepare exclude_ids for viewed or favorited animals
#     user_favorites = user.get_all_favorites if user else []
#     viewed_content = session.get("VIEWED_CONTENT_LIST", [])
#     exclude_ids = set(viewed_content + user_favorites)

#     # Flatten user preferences for API request
#     flattened_animal_preferences = (
#         api.preprocess_preferences(
#             init_params=init_params.copy(),
#             prefs_obj=get_user_animal_preferences(species_list=animal_types),
#         )
#         if user
#         else {animal_type: None for animal_type in animal_types}
#     )

#     # Ensure animal_types is always a list
#     animal_types = [animal_types] if isinstance(animal_types, str) else animal_types
#     next_urls = session.get(
#         NEXT_ANIMAL_URLS_KEY, {animal_type: None for animal_type in animal_types}
#     )

#     # Initialize generator with new parameters, including location
#     generator = api.animal_pagination_generator(
#         animal_types=animal_types,
#         target_count=target_count,
#         init_params=init_params,
#         next_urls=next_urls,
#         exclude_ids=exclude_ids,
#         flattened_animal_preferences=flattened_animal_preferences,
#         location_dict=location_data,
#     )

#     render_content = []
#     no_api_content = False

#     try:
#         for data in generator:
#             if "error" in data:
#                 # Flash the error message
#                 flash(
#                     f"Error fetching data for {data['animal_type']}: {data['error']}",
#                     "error",
#                 )
#                 # Optionally, append partial results if desired
#                 render_content.extend(data.get("partial_results", []))
#             else:
#                 # Accumulate full results
#                 render_content.extend(data)

#         while len(render_content) < target_count:
#             results, next_urls = next(generator)
#             session[NEXT_ANIMAL_URLS_KEY] = next_urls  # Save updated next URLs in session

#             if not results:
#                 no_api_content = True
#                 break  # Exit if generator returns no content

#             # Filter and parse results
#             filters = create_user_preference_filters()
#             filtered_results, success_flag = api.filter_parse_animal_results(
#                 results, filter_prefs=filters
#             )
#             render_content.extend(filtered_results)

#             # Add viewed content to session if successful
#             if success_flag:
#                 session["VIEWED_CONTENT_LIST"] = list(
#                     set(
#                         session.get("VIEWED_CONTENT_LIST", [])
#                         + [result["id"] for result in filtered_results]
#                     )
#                 )
#                 break

#         # No content message
#         if no_api_content:
#             flash(
#                 "No animals found matching your filters. Adjust filters or try again later!",
#                 "warning",
#             )
#             init_params = {"limit": target_count}

#             # Attempt backup API call if no content
#             try:
#                 backup_results = api._get_request(
#                     "animals", f"{api.BASE_API_URL}/animals", params=init_params
#                 )
#                 if not backup_results:
#                     return redirect(
#                         url_for(
#                             "custom_error",
#                             error_title="PetFinder API Unavailable",
#                             error_subtitle="We're sorry for the inconvenience.",
#                             error_message="PetFinder's API is temporarily down. Please try again later.",
#                         )
#                     )
#                 render_content = backup_results.get("animals", [])
#             except Exception as api_error:
#                 app.logger.error(f"API Backup Call Failed: {api_error}")
#                 return redirect(
#                     url_for(
#                         "custom_error",
#                         error_title="PetFinder API Error",
#                         error_subtitle="Unable to retrieve animals.",
#                         error_message="Our system is currently experiencing issues connecting to PetFinder. Please try again later.",
#                     )
#                 )

#         # Respond with JSON for AJAX or render HTML
#         if request.is_json:
#             return jsonify(
#                 {"results": render_content, "success_flag": bool(render_content)}
#             )

#         return render_template("results.html", animals=render_content)

#     except Exception as e:
#         app.logger.error(f"Error at endpoint {request.endpoint}: {e}")
#         return redirect(
#             url_for(
#                 "custom_error",
#                 error_title="Unexpected Error",
#                 error_subtitle="We ran into an issue!",
#                 error_message="Our system encountered an issue loading animals. Please try refreshing the page or come back later.",
#             )
#         )


@app.route("/discover/animals/<animal_type>")
def discover_specific_animal_type(animal_type):
    types_key = "API_ANIMAL_TYPES"
    types_list = session.get(types_key) or json.loads(os.environ.get(types_key, "[]"))

    # Validate animal_type
    if not types_list:
        # Make request to seed animal_types
        seed_animal_info()
        # Retry request to route
        return redirect(
            url_for("discover_specific_animal_type", animal_type=animal_type)
        )

    prettified_animal_type = api.prettify_animal_type(animal_type)

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
        app.logger.error(f"{request.url} error: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred."}), 500


@app.route("/test/animals")
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


@app.route("/test/animals/locations")
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
        app.logger.error(f"{request.url} error: {e}", exc_info=1)
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


@app.route("/loading")
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


@app.route("/data/animal_types", methods=["GET"])
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


@app.route("/data/<country>/state", methods=["GET"])
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
@app.route("/data/prefs/<animal_type>", methods=["GET"])
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


@app.route("/reseed_db", methods=["GET"])
def reseed_db():
    """
    recreate db
    """

    app.logger.info("recreating db by dropping & recreating tables")

    # drop and recreate all tables
    db.drop_all()
    db.create_all()

    test_user = {
        "username": "test123",
        "email": "test123@test123.com",
        "bio": "test123",
        "password": "test123",
        "animal_types": ["dog"],
        "image_url": "../static/images/profile-images/default-hero-sasha-sashina-YCsh4ltV9Ec-unsplash.jpg",
        "rescue_action_type": ["volunteering", "donation", "adoption", "animal foster"],
    }

    test_user_location = default_session_keys["DEFAULT_LOCATION"]

    default_animal_prefs = [
        {"declawed": False},
        {"shots_current": False},
        {"special_needs": False},
        {"spayed_neutered": False},
        {"house_trained": False},
        {"child_friendly": False},
        {"dogs_friendly": False},
        {"cats_friendly": False},
        {"breeds": ["any"]},
        {"colors": ["any"]},
        {"coat": ["any"]},
        {"age": ["any"]},
        {"gender": ["any"]},
        {"size": ["any"]},
        {"personality": ["any"]},
    ]
    # Creating a list of user preferences
    test_user_animal_prefs = [
        {
            "user_id": 1,  # assuming test123 id is "1"
            "species": test_user["animal_types"][0],
            "user_preference_name": list(pref.keys())[0],
            "user_preference_data": list(pref.values())[0],
        }
        for pref in default_animal_prefs
    ]

    # create user
    # test_user["password"] = bcrypt.generate_password_hash(
    #     password=test_user["password"]
    # ).decode("utf8")
    test123 = User.signup(**test_user)
    db.session.add(test123)
    db.session.commit()
    app.logger.info(f"created user: test123 {test123}")

    # create location
    test123_location = UserLocation(**test_user_location)
    db.session.add(test123_location)
    test123.location = test123_location
    db.session.commit()
    app.logger.info(f"created location: test123_location {test123_location}")

    # create prefs
    test123_prefs = db.session.bulk_insert_mappings(
        UserAnimalPreferences, test_user_animal_prefs
    )

    return jsonify(
        {
            "message": "database recreated and user test123 inserted",
            "user": {"id": test123.id, **test_user},
            "location": test_user_location,
            "animal_prefs": test_user_animal_prefs,
        }
    )


@app.route("/discover/orgs", methods=["GET", "POST"])
def discover_orgs():
    # grab current page_count in session
    current_page_count = session.get("CURRENT_DISCOVER_ORGS_PAGE", 1)
    if request.method.upper() == "GET":
        # direct to current page count
        return redirect(url_for("discover_orgs_page", page=current_page_count))


@app.route("/discover/orgs/<int:page>", methods=["GET"])
def discover_orgs_page(page):
    # args = request.args if request.args else {}

    # # handle no page
    # if not page:
    #     page = session.get("CURRENT_DISCOVER_ORGS_PAGE", 1)
    #     if args and "next" in args:
    #         # increment page
    #         page = page + 1
    #         # update session
    #         session["CURRENT_DISCOVER_ORGS_PAGE"] = page
    #     if args and "prev" in args:
    #         # increment page
    #         page = page - 1
    #         # update session
    #         session["CURRENT_DISCOVER_ORGS_PAGE"] = page
    # # handle invalid page attempts & or if the user hasn't visited page 1 yet
    # if not "ANIMAL_RESULTS_DICT" in session:
    #     flash("Sorry, we haven't found that many friends to adopt yet!")
    #     # make post request to seed
    #     requests.post(url_for("discover_orgs"))
    #     sleep(3)
    #     redirect(url_for("discover_orgs_page", page=page))

    # animal_id_list = session.get("ANIMAL_RESULTS_DICT").get(page, [])

    # animals = petpy.animals(animal_id=animal_id_list)

    # return render_template("animalResults.html", animals=animals)

    return jsonify({"THIS IS UNDER DEVELOPMENT"})


@app.route("/data/orgs", methods=["GET", "POST"])
def orgs_data():
    # """ROUTE TO GET ORGS DATA

    # Args:
    #     type (STR): string of either 'animal', 'animals', 'org', 'orgs' that determine the type of PetFinder API call being made

    # Returns:
    #     _type_: _description_
    # """
    # if "CURR_USER" in session:
    #     country = get_user_preference(key="country", session=session, g=g)
    #     state = get_user_preference(key="state", session=session, g=g)
    # else:
    #     country = get_anon_preference(key="country", session=session, g=g)
    #     state = get_anon_preference(key="state", session=session, g=g)

    # api =PetFinderAPI()
    # orgs_search_args = {"country": country, "state": state, "sort": "distance"}
    # if "org_id" in request.args:
    #     orgs_search_args["id"] = request.args["org_id"]

    # org_results = api.organizations(**orgs_search_args)["organizations"]
    # print([(org.name, org.adoption.policy) for org in org_results])
    # return jsonify(org_results)
    return jsonify({"THIS IS UNDER DEVELOPMENT"})


@app.route("/set_location", methods=["POST"])
def set_location():
    """Route to set location for search results

    Returns:
        _type_: _description_
    """
    # grab location from request body
    location = request.values.get(
        "location"
    )  # Use request.values for a combined view of query and form data.

    # handle lack of location provided from request body
    if not location:
        # check if country, state is provided in request body
        country = request.values.get("country", None)
        state = request.values.get("state", None)
        postal_code = request.values.get("postal_code", None)
        geolocation = request.values.get("geolocation", None)

        location = ",".join(country, state)

    # set location in session
    session[USER_LOCATION_KEY] = location

    success_msg = f"App.py: Current CURR_LOCATION set to: {session['CURR_LOCATION']}"
    add_location_to_g(session=session, g=g)

    return jsonify({"message": success_msg})


@app.route("/set_global", methods=["GET", "POST"])
def set_global():
    """Route to set the global options for country of origin and animal types

    If GET -> return form page
    If POST -> set 'country' and/or 'animal_types' in sessions

    """

    # Check if the user is logged in
    if active_authenticated_user():

        animal_types = (
            session.get("ANIMAL_TYPES")
            if "ANIMAL_TYPES" in session
            else current_user.animal_types
        )
        state_country = (
            session.get("STATE_COUNTRY", "ON, CA🍁")
            if "STATE_COUNTRY" in session
            else current_user.location.city_state_country_str()
        )

        form = UserExperiencesForm(animal_types=animal_types, country=country)
    else:
        # check db, session and 'g' for ANON preferences. if not found, will return default country : 'CA'
        country = get_anon_preference(key="country", session=session, g=g)
        animal_types = get_anon_preference(key="animal_types", session=session, g=g)
        form = AnonExperiencesForm(country=country, animal_types=animal_types)

    # Validate form submission
    if form.validate_on_submit():
        # Save preferences for logged-in users
        if "CURR_USER" in session:
            update_user_preferences(form=form)
            return redirect(url_for("home.html"))
        else:
            # Redirect anonymous users to login if animal types are selected
            if isinstance(form.animal_types.data, list):
                return redirect(url_for("login"))
            else:
                # Set global country and animal type for anonymous users
                update_anon_preferences(form=form)

    return render_template(
        "users/form.html", form=form, next=url_for("discover_animals")
    )


##############################################################################
@app.route("/signup", methods=["GET"])
def signup():
    """Route to redirect any signup links that need to be updated
    TO BE REMOVED BEFORE PRODUCTION

    Returns:
        redirect to signup_user Flask Route.
    """
    return redirect(url_for("signup_user"))


@app.route("/signup/user", methods=["GET", "POST"])
def signup_user():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    # instantiate add user form
    form = UserAddForm()
    if form.validate_on_submit():
        data = {field.name: field.data for field in form}
        try:

            user = User.signup(**data)
            # save user location
            user_location = UserLocation(
                user_id=user.id, country=form.country.data, state=form.state.data
            )
            # link user_location to user
            user.location = user_location

            # save new user & location to db
            db.session.add(user)
            db.session.add(user_location)
            db.session.commit()

            # seed animal_preferences for the user
            UserAnimalPreferences.seed_user_pref(user_id=user.id)

            # init_orgs =PetFinderAPI.get_orgs_df()
        except IntegrityError:
            flash("Username already taken", "danger")
            db.session.rollback()
            return render_template("users/signup.html", form=form)

        do_login(user)
        flash("User # {user.id} created successfully: {user.username}", "success")
        # Redirect to location form for additional information
        flash(
            "Please consider enabling geolocation in the browser to help us return more accurate results relative to your location",
            "warning",
        )
        return redirect(url_for("update_user_location"))

    else:

        db.session.rollback()
        return render_template(
            "users/signup.html",
            form=form,
            page_scripts=[
                url_for("static", filename="geolocation.js"),
                url_for("static", filename="setStateCountryInput.js"),
            ],
            next=True,
        )


@app.route("/signup/preferences", methods=["GET", "POST"])
def signup_preferences():
    """Route to return form for user location (state + country), animal_types

    Returns:
        _type_: _description_
    """
    u_pref_form = UserExperiencesForm()

    if u_pref_form.validate_on_submit():
        # Process u_pref_form submission

        # save form data to g, flask sessions and database
        update_user_preferences(
            form=u_pref_form, session=session, user=session["CURR_USER"]
        )  # pass in a current user

    return render_template("users/form.html", form=u_pref_form, next=False)


@login_required
@app.route("/users/preferences/<animal_type>", methods=["GET", "POST"])
def animal_preferences(animal_type):
    if request.method == "GET":
        user_animal_prefs = UserAnimalPreferences.get_user_animal_pref_obj(
            u_id=current_user.id, animal_type=animal_type
        )

    if request.method == "POST":
        # list of SpecificAnimalPreferences field names
        form_field_names = [
            "user_id",
            "species",
            "declawed",
            "shots_current",
            "special_needs",
            "spayed_neutered",
            "house_trained",
            "child_friendly",
            "dogs_friendly",
            "cats_friendly",
            "breeds",
            "color",
            "coat",
            "age",
            "personality_tags",
            "size",
            "gender",
        ]
        # create data obj from request.form to be passed into the  WTForms class
        submitted_data = {
            key: request.form[key] for key in request.form if key in form_field_names
        }
        # create a new flask WTForms instance to prevent submitted form data from being overridden by user_animal_prefs
        form = SpecificAnimalPreferencesForm(animal_type, obj=submitted_data)
    else:
        if "user_id" in user_animal_prefs:
            del user_animal_prefs["user_id"]
        if "species" in user_animal_prefs:
            del user_animal_prefs["species"]
        form = SpecificAnimalPreferencesForm(animal_type, MultiDict(user_animal_prefs))

    if form.validate_on_submit():
        try:
            new_prefs = UserAnimalPreferences.update_user_pref(
                user_id=current_user.id,
                species=animal_type,
                form_data_obj=form.data,
            )
            print(new_prefs)
            # reset current_animal_page count to 1
            session.pop("CURRENT_DISCOVER_ANIMALS_PAGE", 1)

            flash(f"Successfully updated {animal_type} preferences.", "success")
            # return redirect(url_for("animal_pref_data", animal_type=animal_type))
            return redirect(url_for("show_user", user_id=current_user.id))
        except Exception as e:
            app.logger.error(f"Error updating preferences: {e}")
            db.session.rollback()
            flash(
                "An error occurred while saving your preferences. Please try again.",
                "danger",
            )
            return redirect(url_for("profile"))

    return render_template(
        "/users/user_animal_preferences.html", form=form, endpoint_param=animal_type
    )


##############################################################################
# Homepage and error pages


@app.route("/")
def homepage():
    """Show homepage:"""

    offcanvas_form = UserExperiencesForm()
    
    if active_authenticated_user():
        # grab user
        user = current_user._get_current_object().serialize()
        user = user if user else load_user(user_id=current_user.id)

        # set session with user data
        load_session()

        return render_template("home.html", user=user, form=offcanvas_form)
    else:
        return render_template("home-anon.html")  # , results=results


# ERROR routes ##############################################################################
def handle_error(e):
    """Handle both HTTP exceptions and other exceptions."""
    error_code = e.code if isinstance(e, HTTPException) else 500
    error_details = {
        400: {
            "error_title": "400 Bad Request",
            "error_subtitle": "Oops! That's an invalid request.",
            "error_message": "The server couldn't understand your request. Please check your input and try again.",
            "redirect_url": "/",
            "redirect_text": "Back to Home",
        },
        401: {
            "error_title": "401 Unauthorized",
            "error_subtitle": "Access Denied",
            "error_message": "You don't have permission to access this resource. Please log in or check your credentials.",
            "redirect_url": "/login",
            "redirect_text": "Login",
        },
        403: {
            "error_title": "403 Forbidden",
            "error_subtitle": "Access Restricted",
            "error_message": "You don't have permission to access this resource.",
            "redirect_url": "/",
            "redirect_text": "Back to Home",
        },
        404: {
            "error_title": "404 Not Found",
            "error_subtitle": "Oops! Page not found.",
            "error_message": "The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.",
            "redirect_url": "/",
            "redirect_text": "Back to Home",
        },
        500: {
            "error_title": "500 Internal Server Error",
            "error_subtitle": "Oops! Something went wrong.",
            "error_message": "We're experiencing some technical difficulties. Please try again later or contact support if the problem persists.",
            "redirect_url": "/",
            "redirect_text": "Back to Home",
        },
    }

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


# Register the error handler for all HTTP exceptions
@app.errorhandler(HTTPException)
def http_error_handler(e):
    return handle_error(e)


# Register a catch-all error handler for any other exceptions
@app.errorhandler(Exception)
def internal_error_handler(e):
    return handle_error(e)


@app.route("/error")
def custom_error():
    """Route to handle custom errors and redirects from other routes."""
    error_title = request.args.get("error_title", "Error")
    error_subtitle = request.args.get("error_subtitle", "Something went wrong")
    error_message = request.args.get("error_message", "An unexpected error occurred.")
    redirect_url = request.args.get("redirect_url", "/")
    redirect_text = request.args.get("redirect_text", "Return Home 🏡")

    return render_template(
        "error_page.html",
        error_title=error_title,
        error_subtitle=error_subtitle,
        error_message=error_message,
        redirect_url=redirect_url,
        redirect_text=redirect_text,
    )


##############################################################################


def init_default_session():
    """Initialize the session with default values"""
    # clear session
    do_logout()
    # populate with default_session_keys
    for key, value in default_session_keys.items():
        session.setdefault(key, value)
    session["STATE_COUNTRY"] = f"{default_session_keys['location']}"
    session.new = True
    session.modified = True


@app.before_request
def seed_animal_info():
    """Make API call for animal types information and save it to session and environment."""
    types_key = "API_ANIMAL_TYPES"

    # Retrieve type list from session or environment
    type_list = (
        session.get(types_key) or json.loads(os.environ.get(types_key, "[]")) or None
    )

    if not type_list and types_key not in session and types_key not in os.environ:
        # make API call if
        type_list = api.seed_animal_types()

        # Store the type_list in session and environment
        session[types_key] = type_list
        os.environ[types_key] = json.dumps(type_list)


@app.before_request
def load_session():
    """Update the session with user values if user else populates with default values"""

    # populate with default for anon-users for new sessions
    if not active_authenticated_user() and session.new == True:
        return init_default_session()
    else:
        user_id = (
            current_user.id
            if (
                active_authenticated_user()
                and (session.new == True or session.modified == True)
            )
            else None
        )
        user_session_data = current_user._get_current_object().serialize()
        if user_session_data:
            # update session with state_country, animal_types, curr_location, distance
            session.update(user_session_data)


animal_colors = {
    "dog": "primary",
    "cat": "secondary",
    "rabbit": "success",
    "small-furry": "danger",
    "horse": "warning",
    "bird": "info",
    "scales-fins-other": "light",
    "barnyard": "dark",
}


# Inject context into Jinja templates to ensure that Flask session and 'g' object is available without having to manually pass as param into every template
@app.context_processor
def inject_global_vars():
    """Injects the session and g objects into the Jinja2 template context"""
    # print('template context processor being called', session['CURR_USER'])
    return {
        "session": session,
        "g": g,
        "animal_types": api.animal_types,
        "animal_emojis": api.animal_emojis,
        "animal_colors": animal_colors,
        "animal_default_photos": {
            "dog": "dog-freepik.png",
            "cat": "cat-freepik.png",
            "horse": "horse-freepik.png",
            "bird": "bird-eucalyp.png",
            "small-furry": "small-furry-freepik.png",
            "scales-fins-other": "scales-smashicons.png",
            "barnyard": "scales-smashicons.png",
            "rabbit": "rabbit-freepik.png",
            "misc": "tracks_freepik.png",
        },
        "animal_border_colors": {
            key: "border-" + value for key, value in animal_colors.items()
        },
        "animal_bg_colors": {
            key: "bg-" + value for key, value in animal_colors.items()
        },
        "animal_btn_colors": {
            key: "btn-" + value for key, value in animal_colors.items()
        },
        "CURR_USER": (
            current_user._get_current_object()
            if (active_authenticated_user() and current_user)
            else None
        ),
        "user_auth_status": active_authenticated_user(),
        "default_prettified_animal_types": Parse.get_default_prettified_animal_types,
    }


# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask
@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers["Cache-Control"] = "public, max-age=0"
    return req


if __name__ == "__main__":
    flask_env = os.environ.get("FLASK_ENV", "development")
    app.logger.warning(f"Starting app with FLASK_ENV={flask_env}")

    # #for testing / dev purposes, drop and recreate the db tables
    # db.drop_all()
    # db.create_all()

    # run app
    if flask_env == "production":
        app.run(
            host=os.environ.get("HOST", "localhost"),
            port=os.environ.get("PORT", 8000),
        )
    else:
        app.run(
            use_reloader=True,
            host=os.environ.get("HOST", "localhost"),
            port=os.environ.get("PORT", 5000),
        )
