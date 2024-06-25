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
)

# from flask_font_awesome import FontAwesome
from sqlalchemy.exc import IntegrityError, NoResultFound  # type: ignore
from dotenv import load_dotenv  # type: ignore
import pdb  # MAKE SURE TO REMOVE IN PRODUCTION
import os
import requests
import click
import sys

from models import (
    db,
    User,
    UserLocation,
    # UserPreferences,
    UserAnimalPreferences,
    # UserAnimalBehaviorPreferences,
    # UserAnimalAppearancePreferences,
)
from forms import (
    UserAddForm,
    LoginForm,
    UserEditForm,
    UserExperiencesForm,
    UserLocationForm,
    AnonExperiencesForm,
    SpecificAnimalPreferencesForm,
)
from package.helper import (
    data_bp,
    get_anon_preference,
    get_user_preference,
    get_init_api_data,
    update_anon_preferences,
    update_user_preferences,
    # update_global_variables,  # currently here in app.py
    # add_user_to_g,
    # add_location_to_g,
    # add_animal_types_to_g,
)
from package.PetFinderAPI import PetFinderPetPyAPI
from routes.users import users_bp
from routes.auth import auth_bp, do_login
from routes.results import results_bp

CURR_USER_KEY = os.environ.get("CURR_USER_KEY", "curr_user")

# RESOLVE THIS: commented out font_awesome as there an import error to be resolved
# font_awesome = FontAwesome(app)
from config import config, Config

load_dotenv()

# #initialize instance of petFinderPetPyAPI wrapper with helper get functions from helper.py to avoid circular imports
pf_api = PetFinderPetPyAPI(
    get_anon_preference_func=get_anon_preference,
    get_user_preference_func=get_user_preference,
)


def init_session(session):
    """Helper function to set default key-values in Flask session

    Args:
        session (Object): Flask session
    """
    default_session_keys = {
        "location": os.environ.get('CURR_LOCATION', "ON,CA"),
        "state": os.environ.get("state", "ON"),
        "country": os.environ.get("country", "CA"),
        "animal_types": os.environ.get("animal_types", ["dog"]),
    }
    for key, value in default_session_keys.items():
        session.setdefault(key, value)
    
    return print(session.items())

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
    app.register_blueprint(users_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(results_bp)
    
    #init default session values
    init_session(session)
    return app


# app = create_app()
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
app_config_instance.config_app(app=app, obj=config[flask_env_type])  # type: ignore

##############################################################################

# Route to handle form submissions and API calls
@app.route("/submit_section", methods=["POST"])
def submit_section():
    section_data = request.params
    # Make API call using section_data
    mapped_preferences_data = pf_api.map_user_form_data(section_data)
    api_data = pf_api.petpy_api.animals(**mapped_preferences_data)
    # Store API data in session
    session["api_data"] = api_data
    return "API data received"


@app.route("/set_location", methods=["POST"])
def set_location():
    """Route to set location for anonymous search results

    Returns:
        _type_: _description_
    """
    # grab location from request body
    location = request.args.get("location")
    # handle lack of location provided from request body
    if not location:
        # check if country, state is provided in request body
        country = request.args.get("country")
        state = request.args.get("state")
        # if country, state not provided in request body, grab location from .flaskenv
        if not country or not state:
            session["CURR_LOCATION"] = os.environ.get("CURR_LOCATION", "ON,CA")
        # if country, state provided in request body, join and set as location
        else:
            location = ",".join(country, state)

    # set location in session
    session["CURR_LOCATION"] = location
    print(f'App.py: Current CURR_LOCATION set to: {session["CURR_LOCATION"]}')
    return add_location_to_g()


@app.route("/set_global", methods=["GET", "POST"])
def set_global():
    """Route to set the global options for country of origin and animal types

    If GET -> return form page
    If POST -> set 'country' and/or 'animal_types' in sessions

    """

    # Check if the user is logged in
    if g.user:

        # check db, session and 'g' for user preferences. if not found, will return default country : 'CA', animal_type: 'dog'
        country = get_user_preference(key="country")
        animal_types = get_user_preference(key="animal_types")
        form = UserExperiencesForm(animal_types=animal_types, country=country)
    else:
        # check db, session and 'g' for ANON preferences. if not found, will return default country : 'CA'
        country = get_anon_preference(key="country")
        animal_types = get_anon_preference(key="animal_types")
        form = AnonExperiencesForm(country=country, animal_types=animal_types)

    # Validate form submission
    if form.validate_on_submit():
        # Save preferences for logged-in users
        if g.user:
            update_user_preferences(form=form)
            return redirect(url_for("home.html"))
        else:
            # Redirect anonymous users to login if animal types are selected
            if isinstance(form.animal_types.data, list):
                return redirect(url_for("login"))
            else:
                # Set global country and animal type for anonymous users
                update_anon_preferences(form=form)

    return render_template("users/form.html", form=form, next=url_for("data"))

@app.route("/carousel", methods=["GET", "POST"])
def carousel_form_test():
    form = UserAddForm()

    return render_template("carousel-form.html", form=form)


@app.route("/preferences/animal_preferences/<animal_type>", methods=["GET", "POST"])
def animal_preferences(animal_type):
    form = SpecificAnimalPreferencesForm()
    # Query the PetFinder API to get breeds based on the selected animal types
    breed_choices = pf_api.petpy_api.breeds(animal_type)
    api_form_choices = pf_api.petpy_api.animal_types(animal_type)
    coat_choices = api_form_choices.coat
    coat_color_choices = api_form_choices.colors

    print(animal_type)
    if breed_choices:
        print(breed_choices)
        # Populate breed choices in the form
        form.AppearancePreferencesSection.breeds.choices = [
            (name, name.capitalize()) for name in breed_choices
        ]
    if coat_choices:
        form.AppearancePreferencesSection.color.choices = [
            (name, name.capitalize()) for name in coat_choices
        ]
    if coat_color_choices:
        form.AppearancePreferencesSection.color.choices = [
            (name, name.capitalize()) for name in coat_color_choices
        ]

    if form.validate_on_submit():
        # Process form submission
        for section_name, section in form.sections.items():
            for field_name, field in section._fields.items():
                user_preference_name = f"{section_name}_{field_name}"
                user_preference_data = field.data

                # Check if the user already has preferences for this field
                existing_preference = UserAnimalPreferences.query.filter_by(
                    user_id=g.user.id, user_preference_name=user_preference_name
                ).first()
                if existing_preference:
                    # Update existing preference
                    existing_preference.user_preference_data = user_preference_data
                else:
                    # Create new preference
                    new_preference = UserAnimalPreferences(
                        user_id=g.user.id,
                        species=animal_type,
                        user_preference_name=user_preference_name,
                        user_preference_data=user_preference_data,
                    )
                    db.session.add(new_preference)

        db.session.commit()

        # Redirect to the next form or route
        return redirect(url_for("users_show"))

    return render_template("animal_preferences.html", form=form)


##############################################################################
# Homepage and error pages


@app.route("/")
def homepage():
    """Show homepage:

    - anon users:
    - logged in:
    """
    print(g)

    if "user" in g:
        # users_followed_by_current_user = g.user.following

        # Now, you can use this list of users to get their messages

        return render_template("home.html", user=g.user)

    else:
        # try:
        # params = {**pf_api.default_options_obj}
        # # results = pf_api.petpy_api.organizations(sort='-recent')#, country="CA", city="Toronto", state='ON')
        # results = pf_api.get_orgs_df(**params)
        # print(results)
        # except Exception as e:
        #     results = None

        return render_template(
            "home-anon.html", animal_emojis=pf_api.animal_emojis
        )  # , results=results


##############################################################################


def add_user_to_g(session=session, g=g):
    """Add current user to 'g'."""
    if CURR_USER_KEY in session:
        g.user = User.query.get_or_404(session[CURR_USER_KEY])
    else:
        g.user = None


def add_animal_types_to_g(session=session, g=g):
    """Add animal types preferred by the user to 'g'."""
    key = "animal_types"
    if key in session:
        g.animal_types = session[key]
    else:
        # check if user logged in
        if CURR_USER_KEY in session:
            # grab default animal_types
            g.animal_types = get_user_preference(key=key, session=session, g=g)
        else:
            g.animal_types = get_anon_preference(key=key, session=session, g=g)


def add_location_to_g(session=session, g=g):
    """Add CURR_LOCATION to 'g' and session
    Updates the CURR_LOCATION in session to give the app a location context for all API queries
    Does not return anything.
    """
    key = "location"

    # grab any saved location preference using helper function (will return anon_preference results if not logged in)
    location = get_user_preference(key=key, session=session, g=g)
    #handle if location is an db.Model Object instance
    if isinstance(location, db.Model):
        location = location.getLocStr()
    if isinstance(location, str):
        location = location
    # update session and g
    session["CURR_LOCATION"] = location
    g.location = location


@app.before_request
def update_global_variables(session=session, g=g):
    """Initialize or update global variables before each request."""

    add_location_to_g(session=session, g=g)
    add_animal_types_to_g(session=session, g=g)
    add_user_to_g(session=session, g=g)


# Inject context into Jinja templates to ensure that Flask session and 'g' object is available without having to manually pass as param into every template
@app.context_processor
def inject_global_vars():
    """Injects the session and g objects into the Jinja2 template context"""
    return {"session": session, "g": g}


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

##############################################################################
# #Custom APP CLI commands
@app.cli.command("set-env")
@click.option("--env", default="default")
def set_env_cli_command(env):
    """
    This function sets the FLASK_ENV environment variable based on the provided string.
    
    :param env: The `env` parameter is used to specify the environment for the Flask application. 
        # It can take three values: "development", "production", or "default". 
        # The function sets the `FLASK_ENV` environment variable based on the value provided for `env`
    
    Use the Flask CLI to run the command by providing the necessary arguments. 
    Here is an example of how you can call the set-env function in Flask from the command line using the Flask CLI:

    ```bash
    flask set-env --env development
    ```
    """
    #handle if `env` is falsy 
    if not env:
        env = 'default'
    # Function to set the FLASK_ENV environment variable based on the provided string
    if env == "development":
        app.config["FLASK_ENV"] = "development"
        click.echo("FLASK_ENV set to development.")
    elif env == "production":
        app.config["FLASK_ENV"] = "production"
        click.echo("FLASK_ENV set to production.")
    else:
        app.config["FLASK_ENV"] = "default"
        click.echo("FLASK_ENV set to default (default='development').")
##############################################################################

if __name__ == "__main__":
    # handle args to modify flask set-env
    # args = sys.argv 
    # if args[3] and args.lower() in ['prod', 'production', 'test', 'testing', 'tests', 'dev', 'development']:
    #     args = args
    # else: 
    #     args = 'default'
    #set env: eg. "flask set-env --env development"
    # app.cli(args=[f"flask set-env --env {args[1]}"])
    print("FLASK_ENV:", os.environ.get('FLASK_ENV'))
    print("Starting App:", app.config)
    app.run(debug=True, use_reloader=True)
