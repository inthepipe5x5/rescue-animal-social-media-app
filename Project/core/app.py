from flask import (  # type: ignore
    render_template,
    session,
    g,
    jsonify,
)

from flask_login import (
    current_user,
)
from dotenv import load_dotenv  # type: ignore
import os

# from functools import wraps #TODO: to protect certain API routes

# from marshmallow import MarshMallow

from Project.core.methods import (
    active_authenticated_user,
    load_session,
)

from Project.core.constants import (
    default_session_dict,
    default_animal_prefs,
    animal_colors,
    default_animal_types,
    animal_emojis,
    animal_colors,
    default_animal_photos,
)

from Project.models import (
    User,
    UserLocation,
    UserAnimalPreferences,
)

from forms import (
    UserExperiencesForm,
)

from Project.utils.parse import Parse

# import custom exceptions

load_dotenv()


from Project.core import create_app
app = create_app()


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
#         for key, value in default_session_dict.items():
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
@app.route("/")
def homepage():
    """Show homepage:"""

    offcanvas_form = UserExperiencesForm()

    if active_authenticated_user():
        # grab user
        user = current_user._get_current_object().serialize()

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
    from Project.core.extensions import db
    
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
        "rescue_action_type": [
            "volunteering",
            "donation",
            "adoption",
            "animal foster",
        ],
    }

    test_user_location = default_session_dict["DEFAULT_LOCATION"]

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


# Inject context into Jinja templates to ensure that Flask session and 'g' object is available without having to manually pass as param into every template
@app.context_processor
def inject_global_vars():
    """Injects the session and g objects into the Jinja2 template context"""
    # print('template context processor being called', session['CURR_USER'])
    return {
        "session": session,
        "g": g,
        "animal_types": default_animal_types,
        "animal_emojis": animal_emojis,
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


##############################################################################


# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

if __name__ == "__main__":
    flask_env = os.environ.get("FLASK_ENV", "development")

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
