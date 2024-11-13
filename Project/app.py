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
    current_app
)

from flask_login import (
    login_required,
    login_user,
    logout_user,
    current_user,
)
from dotenv import load_dotenv  # type: ignore
import os

# from functools import wraps #TODO: to protect certain API routes

# from marshmallow import MarshMallow

from core import (
    load_user,
    default_session_keys,
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


from flask_migrate import Migrate
from Project.core import db, ma, login_manager, bcrypt, csrf
from Project.api import register_bp

def create_app():
    # create app with factory method
    app = create_app()

    # INITIALIZE EXTENSIONS
    db.init_app(app)
    csrf.init_app(app)
    bcrypt.init_app(app)
    ma.init_app(app)
    login_manager.init_app(app)

    # Set up Flask-Migrate
    migrate = Migrate(app, db, compare_type=True)

    # config flask-login.login manager
    login_manager.login_view = "login"
    # user load function to load user session based on user_id
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    register_bp(app)

    #register routes
    

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


    
    # Inject Custom Jinja filters Here
    custom_filters_dict = {
        "format_kebob_case": Parse.format_kebob_case,
        "prettify_animal_types": Parse.prettify_animal_types,
    }
    for function_key, function in custom_filters_dict.items():
        app.jinja_env.filters[function_key] = function
    
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
    
    @app.after_request
    def add_header(req):
        """Add non-caching headers on every request."""

        req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        req.headers["Pragma"] = "no-cache"
        req.headers["Expires"] = "0"
        req.headers["Cache-Control"] = "public, max-age=0"
        return req



    
    return app




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




# TODO # FIX LATER
# @app.route("/static/images/graphics/<path:filename>")
# def serve_image(filename):
#     return send_from_directory(IMAGE_FOLDER, f"/{filename}")



##############################################################################
# Homepage and error pages


##############################################################################



# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

if __name__ == "__main__":
    flask_env = os.environ.get("FLASK_ENV", "development")
    app = create_app()
    
    app.logger.warning(f"Starting app with FLASK_ENV={flask_env}")

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
