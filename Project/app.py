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
import requests
from time import sleep

# from functools import wraps #TODO: to protect certain API routes
from flask_bcrypt import Bcrypt
from werkzeug.datastructures import MultiDict

from models import (
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
from package.PetFinderAPI import PetFinderPetPyAPI
from package.parse import Parse


CURR_USER_KEY = os.environ.get("CURR_USER_KEY", "curr_user")


load_dotenv()

default_session_keys = {
    "CURR_LOCATION": os.environ.get("CURR_LOCATION", "43.6429,-79.3889"),
    "ANIMAL_TYPES": os.environ.get("ANIMAL_TYPES", ["dog"]),
    "CURRENT_DISCOVER_ANIMALS_PAGE": 1,
    "CURRENT_DISCOVER_ORG_PAGE": 1,
    "DEFAULT_LOCATION": {
        "geolocation": "43.6429,-79.3889",
        "state": "ON",
        "country": "CA",
        "postal_code": "m5j0b3",
        "city": "Toronto",
    },
    "DISTANCE_PREF": 100,
    "RESULTS_PER_PAGE": 6,  # default is 6 (so render 2 rows of 3 columns of cards)
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

#Custom Jinja filters
custom_filters_dict = {
    "format_kebob_case": Parse.format_kebob_case,
}
for function_key, function in custom_filters_dict.items():
    app.jinja_env.filters[function_key] = function 

# api instance of helper class
api = PetFinderPetPyAPI()

# petpy instance
petpy = Petfinder(key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET"))

#set auth in petpy
if not petpy._auth:
    petpy._auth = os.environ.get('ACCESS_TOKEN', None)
    
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
    # session.update("CURR_LOCATION", user.location.city_state_country_str())
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
        "ANIMAL_TYPES", default=os.environ.get("ANIMAL_TYPES", ["dog"])
    )  # reset CURR_LOCATION
    session.pop("CURR_LOCATION", default=os.environ.get("CURR_LOCATION", "Toronto, ON"))
    # app.logger.info(f"do_logout successful. Session[CURR_USER]=", (session["CURR_USER"] if "CURR_USER" in session  else None))
    g.pop("user", None)
    # clear session and create new session
    session.clear()
    session.new = True

    # flask-login's logout user => will clean up the cookie if it exists
    logout_user()


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


@login_required
@app.route("/users/location", methods=["GET", "POST"])
def form_user_location():
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
        app.logger.error(f"Error in form_user_location: {str(e)}")
        db.session.rollback()
        flash(
            "An error occurred while updating your location. Please try again.", "error"
        )
        # return redirect(url_for("show_user", user_id=current_user.id))


@login_required
@app.route("/users/travel", methods=["GET", "POST"])
def user_travel_preferences():
    travel_preferences = UserTravelPreferences.query.filter_by(
        user_id=current_user.id
    ).first()

    if not current_user.location:
        flash("Please set your location details first", "warning")
        return redirect(url_for("form_user_location"))

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
        form_title="How far are you willing to travel? Change the distance parameter to have more localized results.",
        page_scripts=[url_for("static", filename="setTravelPreference.js")],
    )


# @app.route("/users/<int:user_id>/favorites")
# def show_favorites(user_id):
#     """Show list of people this user is favorites."""

#     if "CURR_USER" not in session:
#         flash("Access unauthorized.", "danger")
#         return redirect("/")

#     user = User.query.get_or_404(user_id)
#     return render_template("users/favorites.html", user=user)


# @app.route("/users/<int:user_id>/followers")
# def users_followers(user_id):
#     """Show list of followers of this user."""

#     if "CURR_USER" not in session:
#         flash("Access unauthorized.", "danger")
#         return redirect("/")

#     user = User.query.get_or_404(user_id)
#     return render_template("users/followers.html", user=user)


@login_required
@app.route("/users/favorite/all", methods=["POST"])
def all_user_favorites():
    """Add or toggle a favorite for the currently-logged-in user."""
    
    fav_type = request.args.get("type", "animals").lower() if request.args else 'all'

    user = (
        current_user
        if current_user.is_authenticated
        else session.get("CURR_USER", None)
    )
    if not user:
        flash("Access unauthorized.", "danger")
        return redirect(url_for("login"))

    try:
        if fav_type == 'all':
            user_favorites = UserFavorites.get_favorites(user_id=user.id)
        
        #return fave orgs
        elif fav_type.lower() in ('orgs', 'organizations', 'organization', 'rescue', 'rescues'):
            user_favorites = UserFavorites.get_orgs_favorites(user_id=user.id)
        
        #return fave animals if fave_type not specified
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
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


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

@login_required
@app.route("/users/profile", methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if not active_authenticated_user():
        flash("Access unauthorized.", "danger")
        return redirect(url_for("login"))

    else:
        user = session["CURR_USER"]
        logged_in_user = User.query.get(user["id"])
        form = UserEditForm(obj=logged_in_user)

        if form.validate_on_submit():
            if User.authenticate(form.username.data, form.password.data):
                form.populate_obj(logged_in_user)
                db.session.add(logged_in_user)
                db.session.commit()  # commit to db
                flash("Changes saved successfully", "success")  # show success to user
                return redirect(url_for("show_user", user_id=g.user.id))
            else:
                db.session.rollback()
                flash(
                    "You were unsuccessful, try again", "error"
                )  # show success to user
                return render_template(
                    "users/edit.html", form=form, user=logged_in_user
                )

        return render_template("users/edit.html", form=form, user=logged_in_user)

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


def get_user_data(user_id):
    if user_id:
        result = (
            db.session.query(
                User.id,
                User.animal_types,
                UserLocation.state,
                UserLocation.country,
                UserTravelPreferences.distance_filter_preference,
            )
            .join(UserLocation)
            .join(UserTravelPreferences)
            .filter(User.id == user_id)
            .first()
        )
        # debugging
        if result:
            print(f"User ID: {result.id}")
            print(f"Animal Types: {result.animal_types}")
            print(f"State: {result.state}")
            print(f"Country: {result.country}")
            print(f"Distance Filter Preference: {result.distance_filter_preference}")

            current_location = (
                db.session.query(UserLocation)
                .filter(UserLocation.user_id == user_id)
                .first()
            )

            return {
                "CURR_USER_KEY": result.id,
                "ANIMAL_TYPES": result.animal_types,
                "STATE_COUNTRY": f"{result.state+', '+result.country}",
                "DISTANCE_PREF": result.distance_filter_preference,
                "CURR_LOCATION": (
                    current_location.get_location_info()
                    if current_location
                    else default_session_keys["CURR_LOCATION"]
                ),
            }
    # handle no results
    print("No User data found, default output returned")
    default_output = default_session_keys.copy()
    default_output["STATE_COUNTRY"] = get_location(no_geocode=False)
    return default_output


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
            return (
                user_location.city_state_country_str()
            )  # return city/state/str eg. for UI rendering purposes
        else:
            return (
                user_location.get_location_info()
            )  # returns first truthy location column
    # handle anon user
    else:
        if no_geocode:
            return (
                default_session_keys["DEFAULT_LOCATION"]["state"].lower()
                + default_session_keys["CURR_LOCATION"]["country"].lower()
            )
        else:
            return default_session_keys["CURR_LOCATION"]


def create_init_params(type="animal"):
    """
    Dynamically creates and returns a dictionary of initialization parameters for
    API calls based on the user's authentication state, preferences, and location.

    Args:
        type (str): The type of object to fetch ('animal' or 'org'). Default is 'animal'.

    Returns:
        dict: A dictionary of API query parameters including type, page, location, distance, and limit.
    """

    # Helper function to retrieve species preferences or default to 'dog'
    def get_species_preferences(user=None):
        """
        Fetches the user's species preferences, or defaults to 'dog' if no user or no preferences are present.
        Args:
            user (User): Current user object.
        Returns:
            list: List of species.
        """
        return (
            list(user.animal_types)
            if user and user.animal_types
            else list(default_session_keys.get("ANIMAL_TYPES", "dog"))
        )

    # Common session values or default ones
    current_page_count = (
        session.get("CURRENT_DISCOVER_ANIMALS_PAGE", 1)
        if type.lower() in ["animal", "animals"]
        else session.get("CURRENT_DISCOVER_ORGS_PAGE", 1)
    )
    distance_pref = session.get("DISTANCE_PREF", default_session_keys["DISTANCE_PREF"])

    # If the user is authenticated and active
    if active_authenticated_user():
        user = load_user(user_id=current_user.id)
        user_location = (
            user.location
            if user
            else db.session.query(UserLocation)
            .filter_by(user_id=current_user.id)
            .first()
        )

        # Get user-specific data or defaults
        species = get_species_preferences(user)
        location_str = get_location(user_location)
        distance_pref = (
            UserTravelPreferences._get_distance_filter_param(user_id=current_user.id)
            or distance_pref
        )
        status = get_rescue_action_mapped_to_animal_status()
    else:
        # Non-authenticated user, default settings
        species = default_session_keys.get("ANIMAL_TYPES", "dog")
        location_str = os.environ.get("CURR_LOCATION", "43.6429,-79.3889")
        distance_pref = 100

    # Set limit based on species length (more species = more results per page)
    species_len = len(species) or 1
    limit = (15 if 0 < species_len < 8 else 10) * species_len

    # create status param => "adoptable, adopted, found" PetFinderAPI Accepts multiple values (default: adoptable)
    # Return parameters for animal search
    if type.lower() in ("animal", "animals"):
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
    elif type.lower() in ("org", "orgs", "organization", "organizations"):
        output_params = {
            "type": species,
            "page": current_page_count,
            "location": location_str,
            "state": str(
                user_location.state
                if user_location
                else default_session_keys.get("state", "ON")
            ),  # Fallback state to ON
            "country": str(
                user_location.country
                if user_location
                else default_session_keys.get("country", "CA")
            ),  # Fallback country to CA
            "distance": distance_pref,
            "limit": limit,
            "sort": "distance",  # Sort results by distance
        }

        return output_params


# Helper function to retrieve user preferences for animals
def get_user_animal_preferences(user_id=None, species_list=["dog"]):
    """
    Fetches user preferences for each species or returns an empty dictionary.
    Args:
        user_id (int): ID of the current user.
        species_list (list): List of species to query preferences for.
    Returns:
        dict: Dictionary of user preferences keyed by species type.
    """
    if not user_id:
        if active_authenticated_user():
            user_id = current_user.id
        else:
            return None

    user_prefs_query = UserAnimalPreferences.get_all_user_animal_preferences(
        u_id=user_id
    )
    return (
        {species: user_prefs_query for species in species_list}
        if user_prefs_query
        else None
    )


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
                "state": user_location.state,
                "country": user_location.country,
            }
        )
        if user_prefs:
            # Loop through animal types and combine animal & location filters
            for animal_type, preferences in user_prefs.items():
                # Create animal preference filters
                animal_filter = api.create_filter_conditions(preferences=preferences)

                # Combine animal and location filters without nesting under the same key
                filters[animal_type] = {
                    **animal_filter,  # Animal filters for the specific type
                    **location_filters,  # Location filters (state, country)
                }
        else:
            filters = location_filters

        return filters


@app.route("/discover/animals", methods=["GET", "POST"])
def discover_animals():
    # grab current page_count in session
    current_page_count = session.get("CURRENT_DISCOVER_ANIMALS_PAGE", 1)
    if request.method.upper() == "GET":
        # direct to current page count
        return redirect(url_for("discover_animals_page", page=current_page_count))
    elif request.method.upper() == "POST":
        # current user
        user = load_user(current_user.id) if active_authenticated_user() else None

        init_params = create_init_params(type="animal")
        if active_authenticated_user():
            animal_prefs = get_user_animal_preferences(user_id=user.id)
            expanded_params = api.preprocess_preferences(
                init_params_copy=init_params.copy(), prefs_obj=animal_prefs
            )
        # create params for GET request
        animal_params = (
            expanded_params
            if (expanded_params and active_authenticated_user())
            else init_params
        )
        animal_params["count"] = 50  # return 50 results to filter

        filters = (
            {}
            if not animal_prefs
            else api.create_filter_conditions(preferences=animal_prefs)
        )

        try:
            response = api._get_request(params=animal_params)
            if response.get("animals") and len(response.get("animals")) > 0:
                animal_lists = response.get("animals", [])
                filtered = api.filter_results_list(
                    results_list=animal_lists, filter_conditions=filters
                )
                if filtered and filtered.get("results"):
                    all_results = filtered.get("results")
                    results_per_page = session.get("RESULTS_PER_PAGE", 6)
                    paginated_result_object = {}
                    page_index = 1
                    for result in all_results:
                        if page_index in paginated_result_object:
                            if (
                                len(paginated_result_object[page_index])
                                >= results_per_page
                            ):
                                # increment if greater or equal if the length of the list stored under this page_index is greater/equal to the RESULTS_PER_PAGE setting
                                page_index = page_index + 1
                            else:
                                # append result to the object list under the page_index key
                                paginated_result_object[page_index].append(result.id)
                        else:
                            # if page_index not in paginated_result_object, create a list with result
                            paginated_result_object[page_index] = [result.id]

                    if paginated_result_object:
                        # TODO: REMOVE LATER AFTER DEBUGGING
                        app.logger.debug(
                            "animal results in session created", paginated_result_object
                        )

                        # save to session so that future routes can use this
                        session["ANIMAL_RESULTS_DICT"] = paginated_result_object

        except Exception as e:
            app.logger.error("UH OH, something went wrong @ {request.endpoint} - {e}")


@app.route("/discover/animals/<int:page>", methods=["GET"])
def discover_animals_page(page):
    args = request.args if request.args else {}

    # handle no page
    if not page:
        page = session.get("CURRENT_DISCOVER_ANIMALS_PAGE", 1)
        if args and "next" in args:
            # increment page
            page = page + 1
            # update session
            session["CURRENT_DISCOVER_ANIMALS_PAGE"] = page
        if args and "prev" in args:
            # increment page
            page = page - 1
            # update session
            session["CURRENT_DISCOVER_ANIMALS_PAGE"] = page
    # handle invalid page attempts & or if the user hasn't visited page 1 yet
    if not "ANIMAL_RESULTS_DICT" in session:
        flash("Sorry, we haven't found that many friends to adopt yet!")
        # make post request to seed
        requests.post(url_for("discover_animals"))
        sleep(3)
        redirect(url_for("discover_animals_page", page=page))

    animal_id_list = session.get("ANIMAL_RESULTS_DICT").get(page, [])

    animals = api._get_request(animal_id=animal_id_list)

    return render_template("animalResults.html", animals=animals)


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


@app.route("/data/animals", methods=["GET", "POST"])
def animal_data():
    """DATA ROUTE FOR FRONTEND TO GET PETPY API ANIMALS DATA"""
    user = load_user(current_user.id) if active_authenticated_user() else None
    try:
        # Create PetFinder API query params based on user settings saved in session
        init_params = create_init_params(type="animals")

        # grab animal prefs => will return None if no user
        animal_prefs = get_user_animal_preferences(user_id=user.id) or {}

        # grab user favorites if user
        favorites = (
            UserFavorites.get_animal_favorites(user_id=user.id)
            if active_authenticated_user()
            else []
        )

        # Fetch and yield paginated results
        results = api.get_mapped_animals_by_type(
            init_params=init_params,
            favorites=favorites,
            user_preferences_dict=animal_prefs,
            filter_prefs=create_user_preference_filters(),
        )

        # Check if the results are valid
        if (
            not results
            or not isinstance(results, dict)
            or not results["success_flag"]
            or not results["results"]
        ):
            return (
                jsonify(
                    {
                        "success_flag": False,
                        "message": "No results found.",
                        "results": results["results"] if results else [],
                        "bad_keys": results["bad_keys"] if results else [],
                        "unfiltered": not any(
                            [len(results["results"]) > 0, results["success_flag"]]
                        )
                        or results.get(
                            "unfiltered", False
                        ),  # Ensure `unfiltered` key exists
                    }
                ),
                200,
            )

        # Return the batch of results
        return jsonify(results), 200

    except Exception as e:
        err_msg = f"ERROR /data/animals => {str(e)}"
        print(err_msg)
        return (
            jsonify(
                {
                    "success_flag": False,
                    "message": "An error occurred while fetching animal data.",
                    "error": err_msg,
                }
            ),
            500,
        )


# # TESTING/DEBUGGING ROUTE
# @login_required
# @app.route("/data/prefs/animals", methods=["GET"])
# def all_animal_pref_data():

#     if active_authenticated_user():
#         user_id = current_user.id
#     else:
#         # user_id = 18  # user: 99299@99299.com
#         return jsonify(
#             {"results": [], "success_flag": False, "message": "No user logged in"}
#         )
#     user_animal_prefs = UserAnimalPreferences.get_all_user_animal_preferences(
#         u_id=user_id
#     )
#     if user_animal_prefs:
#         message = "User animal preferences retrieved successfully."
#         category = "success"
#     else:
#         message = "No animal preferences found."
#         category = "error"
#     flash(message=message, category=category)
#     # return all user animal_preferences grouped by animal type as found in db
#     # if not clean_bool:
#     #     output = user_animal_prefs if user_animal_prefs else []

#     output = (
#         api.preprocess_preferences(prefs_obj=user_animal_prefs)
#         if user_animal_prefs
#         else []
#     )
#     return jsonify(
#         {
#             "results": output,
#             "message": message,
#             "success_flag": True if category != "error" else False,
#         }
#     )


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
    args = request.args if request.args else {}

    # handle no page
    if not page:
        page = session.get("CURRENT_DISCOVER_ORGS_PAGE", 1)
        if args and "next" in args:
            # increment page
            page = page + 1
            # update session
            session["CURRENT_DISCOVER_ORGS_PAGE"] = page
        if args and "prev" in args:
            # increment page
            page = page - 1
            # update session
            session["CURRENT_DISCOVER_ORGS_PAGE"] = page
    # handle invalid page attempts & or if the user hasn't visited page 1 yet
    if not "ANIMAL_RESULTS_DICT" in session:
        flash("Sorry, we haven't found that many friends to adopt yet!")
        # make post request to seed
        requests.post(url_for("discover_orgs"))
        sleep(3)
        redirect(url_for("discover_orgs_page", page=page))

    animal_id_list = session.get("ANIMAL_RESULTS_DICT").get(page, [])

    animals = petpy.animals(animal_id=animal_id_list)

    return render_template("animalResults.html", animals=animals)


@app.route("/data/orgs", methods=["GET", "POST"])
def orgs_data():
    """ROUTE TO GET ORGS DATA

    Args:
        type (STR): string of either 'animal', 'animals', 'org', 'orgs' that determine the type of PetFinder API call being made

    Returns:
        _type_: _description_
    """
    if "CURR_USER" in session:
        country = get_user_preference(key="country", session=session, g=g)
        state = get_user_preference(key="state", session=session, g=g)
    else:
        country = get_anon_preference(key="country", session=session, g=g)
        state = get_anon_preference(key="state", session=session, g=g)

    api = PetFinderPetPyAPI()
    orgs_search_args = {"country": country, "state": state, "sort": "distance"}
    if "org_id" in request.args:
        orgs_search_args["id"] = request.args["org_id"]

    org_results = api.organizations(**orgs_search_args)["organizations"]
    print([(org.name, org.adoption.policy) for org in org_results])
    return jsonify(org_results)


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
    session["CURR_LOCATION"] = location

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

        animal_types = session.get('ANIMAL_TYPES') if 'ANIMAL_TYPES' in session else current_user.animal_types
        state_country = session.get('STATE_COUNTRY') if 'STATE_COUNTRY' in session else current_user.location
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
            UserAnimalPreferences.seed_user_pref(
                user_id=user.id, form=SpecificAnimalPreferencesForm
            )

            # init_orgs = PetFinderPetPyAPI.get_orgs_df()
        except IntegrityError:
            flash("Username already taken", "danger")
            db.session.rollback()
            return render_template("users/signup.html", form=form)

        do_login(user)
        flash("User # {user.id} created successfully: {user.username}")
        # Redirect to location form for additional information
        flash(
            "Please consider enabling geolocation in the browser to help us return more accurate results relative to your location",
            "warning",
        )
        return redirect(url_for("form_user_location"))

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

    if active_authenticated_user():
        # grab user
        user = current_user._get_current_object()
        user = user if user else load_user(user_id=current_user.id)

        # set session with user data
        load_session()

        return render_template("home.html", user=user)
    else:
        return render_template("home-anon.html")  # , results=results


##############################################################################


def init_default_session():
    """Initialize the session with default values"""
    # clear session
    do_logout()
    # populate with default_session_keys
    for key, value in default_session_keys.items():
        session.setdefault(key, value)
    session["STATE_COUNTRY"] = get_location(no_geocode=False)
    session.new = True
    session.modified = True


# # load user data into session before each request
# def update_session():
#         if session.new: #new session if new session or session dependencies are modified in a route, the route will indicate that it's a new session
#             load_session()


@app.before_request
def load_session():
    """Update the session with user values if user else populates with default values"""

    # populate with default for anon-users for new sessions
    if not active_authenticated_user() and session.new == True:
        return init_default_session()
    else:
        user_id = current_user.id if active_authenticated_user() else None
        user_session_data = get_user_data(user_id=user_id)
        if user_session_data:
            # update session with state_country, animal_types, curr_location, distance
            session.update(user_session_data)


# Initialize global variables before each request
# @app.before_request
# def get_app_data():
#     """Function that runs before each request to refresh global variables and grab initial API data if none

#     Returns:
#         _type_: _description_
#     """
#     # update global variables
#     with app.app_context():
#         if session.modified == True:
#             update_global_variables(session=session, g=g)


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
        "animal_border_colors": {
            "dog": "border-primary",
            "cat": "border-secondary",
            "rabbit": "border-success",
            "small-furry": "border-danger",
            "horse": "border-warning",
            "bird": "border-info",
            "scales-fins-other": "border-light",
            "barnyard": "border-dark",
        },
        "animal_bg_colors": {
            "dog": "bg-primary",
            "cat": "bg-secondary",
            "rabbit": "bg-success",
            "small-furry": "bg-danger",
            "horse": "bg-warning",
            "bird": "bg-info",
            "scales-fins-other": "bg-light",
            "barnyard": "bg-dark",
        },
        "current_user_id": current_user.id if active_authenticated_user() else None,
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
