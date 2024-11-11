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
)

from flask_login import (
    login_required,
    login_user,
    logout_user,
    current_user,
)
from dotenv import load_dotenv  # type: ignore
import os
import pycountry
from time import sleep
import json
from urllib.parse import urljoin

# from functools import wraps #TODO: to protect certain API routes
from werkzeug.exceptions import HTTPException

# from marshmallow import MarshMallow

from Project.core.methods import get_anon_location
from core import (
    load_user,
    default_session_keys,
    CURR_ANIMALS_KEY,
    DEFAULT_LOCATION,
    DISTANCE_KEY,
    RESULTS_PER_PAGE_KEY,
    VIEWED_CONTENT_KEY,
    USER_LOCATION_KEY,
    NEXT_ANIMAL_URLS_KEY,
    API_ANIMAL_TYPES_KEY,
    animal_colors,
    active_authenticated_user,
    default_animal_prefs,
    load_session,
    default_animal_photos,
)

from Project.models import (
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
from services.petfinder.helper import (
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
from .api.routes.pf.pf_bp import mock_pf_bp

from config import config, Config
from services import pf as api
from Project.utils.parse import Parse

# import custom exceptions
from services.petfinder.api_exceptions import (
    PetFinderResourceNotFoundError,
    PetFinderInvalidCredentialsError,
    PetFinderAccessDeniedError,
    PetFinderInvalidParametersError,
    PetFinderLocationError,
    PetFinderUnexpectedServerError,
)
from services.petfinder.petfinder_types import (
    AnimalReqParams,
    AnimalType,
    AnimalTypes,
    FormattedAnimalType,
)


load_dotenv()

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

# Inject Custom Jinja filters Here
custom_filters_dict = {
    "format_kebob_case": Parse.format_kebob_case,
    "prettify_animal_types": Parse.prettify_animal_types,
}
for function_key, function in custom_filters_dict.items():
    app.jinja_env.filters[function_key] = function

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


##############################################################################


# TODO # FIX LATER
# @app.route("/static/images/graphics/<path:filename>")
# def serve_image(filename):
#     return send_from_directory(IMAGE_FOLDER, f"/{filename}")


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


##############################################################################


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
        "animal_default_photos": default_animal_photos,
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
