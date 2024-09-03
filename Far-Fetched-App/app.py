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
import json

from sqlalchemy.exc import IntegrityError, NoResultFound  # type: ignore
from sqlalchemy import and_  # , Index
from dotenv import load_dotenv  # type: ignore
import os
import requests
from functools import wraps
from flask_bcrypt import Bcrypt
from werkzeug.datastructures import MultiDict
from .models import (
    db,
    User,
    UserLocation,
    UserAnimalPreferences,
)
from .forms import (
    UserAddForm,
    LoginForm,
    UserEditForm,
    UserExperiencesForm,
    UserLocationForm,
    AnonExperiencesForm,
    SpecificAnimalPreferencesForm,
)
from .package.helper import (
    data_bp,
    get_anon_preference,
    get_user_preference,
    get_init_api_data,
    update_anon_preferences,
    update_user_preferences,
    update_global_variables,  # currently in helper.py
    add_user_to_g,
    add_location_to_g,
    add_animal_types_to_g,
)
from .package.PetFinderAPI import PetFinderPetPyAPI
from .config import config, Config

CURR_USER_KEY = os.environ.get("CURR_USER_KEY", "curr_user")


load_dotenv()

# #initialize instance of petFinderPetPyAPI wrapper with helper get functions from helper.py to avoid circular imports
pf_api = PetFinderPetPyAPI(
    get_anon_preference_func=get_anon_preference,
    get_user_preference_func=get_user_preference,
)


default_session_keys = {
    "location": os.environ.get("CURR_LOCATION", "ON,CA"),
    "state": os.environ.get("state", "ON"),
    "country": os.environ.get("country", "CA"),
    "animal_types": os.environ.get("animal_types", ["dog"]),
}


def init_session(session):
    """Helper function to set default key-values in Flask session

    Args:
        session (Object): Flask session
    """
    for key, value in default_session_keys.items():
        session.setdefault(key, value)

    app.logger.info(f"Session initialized - {session}")


def reset_session(default_settings_obj):
    """Helper function to RESET back to default key-values in Flask session

    Args:
        default_settings_obj (Object): object of default Flask session key:value settings
    """
    # Clear the current session
    session.clear()

    # If default settings are provided, update the session with them
    if default_settings_obj and isinstance(default_settings_obj, dict):
        session.update(default_settings_obj)

    # Ensure the session is marked as modified
    session.modified = True

    app.logger.info(f"Session reset to default - {session}")


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
        init_session(session)
    return app


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
# app = create_app()
# config bcrypt
bcrypt = Bcrypt(app)


##############################################################################
# User signup/login/logout


def auth_required(route_func):
    @wraps(route_func)
    def protected_route(*args, **kwargs):
        if CURR_USER_KEY not in session:
            # flash error
            flash("Unauthorized", "danger")
            # not authenticated, redirect to login and then requested url once authenticated
            return redirect(url_for("login"), next=request.url)
        # else the user is authenticated and should be allowed to proceed to the protected route
        return route_func(*args, **kwargs)

    return protected_route


def do_login(user):
    """Log in user."""
    # add user.id to session
    session[CURR_USER_KEY] = user.id
    session["CURR_USER"] = user.serialize()  # needs to be JSON serializable to be saved
    g.user = user  # auto calls the Model.serialize()
    # update the other global variables
    # add_animal_types_to_g(session, g)
    # add_location_to_g(session, g)
    update_global_variables(session, g)
    app.logger.info(
        f"do_login({user.username}) successful. Session[CURR_USER]=",
        session["CURR_USER"],
    )


def do_logout():
    """Logout user."""

    session.pop(CURR_USER_KEY, default=None)
    session.pop("CURR_USER", default=None)

    # return stored values to default
    # reset animal types
    session.pop(
        "ANIMAL_TYPES", default=os.environ.get("ANIMAL_TYPES", ["dog"])
    )  # reset CURR_LOCATION
    session.pop("CURR_LOCATION", default=os.environ.get("CURR_LOCATION", "ON,CA"))
    # app.logger.info(f"do_logout successful. Session[CURR_USER]=", (session["CURR_USER"] if "CURR_USER" in session  else None))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)

        if user:
            do_login(user)
            g.user = user
            print(g.user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", "danger")

    return render_template("users/login.html", form=form)


@auth_required
@app.route("/logout")
def logout():
    """Handle logout of user."""
    if CURR_USER_KEY in session:
        print(session[CURR_USER_KEY])
    do_logout()
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
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    return render_template("users/show.html", user=user)


# @app.route("/users/<int:user_id>/following")
# def show_following(user_id):
#     """Show list of people this user is following."""

#     if "CURR_USER" not in session:
#         flash("Access unauthorized.", "danger")
#         return redirect("/")

#     user = User.query.get_or_404(user_id)
#     return render_template("users/following.html", user=user)


# @app.route("/users/<int:user_id>/followers")
# def users_followers(user_id):
#     """Show list of followers of this user."""

#     if "CURR_USER" not in session:
#         flash("Access unauthorized.", "danger")
#         return redirect("/")

#     user = User.query.get_or_404(user_id)
#     return render_template("users/followers.html", user=user)


# @app.route("/users/follow/<int:follow_id>", methods=["POST"])
# def add_follow(follow_id):
#     """Add a follow for the currently-logged-in user."""

#     if "CURR_USER" not in session:
#         flash("Access unauthorized.", "danger")
#         return redirect("/")

#     followed_user = User.query.get_or_404(follow_id)
#     g.user.following.append(followed_user)
#     db.session.commit()

#     return redirect(f"/users/{g.user.id}/following")


# @app.route("/users/stop-following/<int:follow_id>", methods=["POST"])
# def stop_following(follow_id):
#     """Have currently-logged-in-user stop following this user."""

#     if "CURR_USER" not in session:
#         flash("Access unauthorized.", "danger")
#         return redirect("/")

#     followed_user = User.query.get(follow_id)
#     g.user.following.remove(followed_user)
#     db.session.commit()

#     return redirect(f"/users/{g.user.id}/following")


@app.route("/users/profile", methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if "CURR_USER" not in session:
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
                return redirect(url_for("users_show", user_id=g.user.id))
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

    if "CURR_USER" not in session:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(session["CURR_USER"])
    db.session.commit()

    return redirect("/signup")


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


@app.route("/data/animals", methods=["GET", "POST"])
def animal_data():
    """TEST ROUTE TO USE PETPY API

    Args:
        type (STR): string of either 'animal', 'animals', 'org', 'orgs' that determine the type of PetFinder API call being made

    Returns:
        _type_: _description_
    """

    # # country = get_user_preference(key="country", session=session, g=g)
    # # print(country)
    # results = pf_api.petpy_api.animals(location="CA", sort="distance")
    user_id = 18  # session["CURR_USER"].id
    species = "dog"  # session["CURR_USER"].animal_types[0]
    user_prefs = UserAnimalPreferences.get_user_animal_pref_obj(
        u_id=user_id, animal_type=species
    )

    # filter only by breeds for now
    # if "breeds" in user_prefs:
    user_prefs = user_prefs["results"]

    location_str = "CA" #does not work
    geo_coordinates = "43.7190656,-79.347712" #works
    animals = pf_api.petpy_api.animals(animal_type="dog", results_per_page=50, pages=3, location=geo_coordinates)


    filters = pf_api.create_filter_conditions(user_prefs)
    results = pf_api.filter_results_list(
        filter_conditions=filters, results_list=animals["animals"]
    )
    # results = pf_api.get_mapped_animals_by_type(
    #     species=species,
    #     location_str=location_str,
    #     user_preferences_dict={}#user_prefs #user_prefs.get("results"),
    # )
    return jsonify(results)

    # WHEN READY TO DISPLAY IN HTML

    # flash message if not success
    # if not results.success_flag:
    #     flash(f"Your search preferences are too strict; try adjusting {", ".join(results.bad_keys)} In the mean time, here's animals in your area in the mean time.")
    #     # return render_template("results.html", results=results)


# @auth_required
@app.route("/data/prefs/<animal_type>", methods=["GET"])
def animal_pref_data(animal_type):
    if animal_type[-1].lower() == "s":
        species = animal_type.lower()[:-1]
    else:
        species = animal_type.lower()

    if "CURR_USER" in session:
        user_id = session.get("CURR_USER")["id"]
    else:
        user_id = 18  # user: 99299@99299.com

    user_animal_prefs = UserAnimalPreferences.get_user_animal_pref_obj(
        u_id=user_id, animal_type=species
    )
    # output = pf_api.create_filter_conditions(user_animal_prefs["results"])
    return jsonify(user_animal_prefs)
    # else:
    # return redirect(url_for("login"))


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

    salt = bcrypt.gensalt()
    test_user.password = bcrypt(test_user.password.encode("utf-8"), salt)
    test123 = User.signup(**test_user)
    app.logger.info(f"created user: test123 {test123}")
    test123_location = UserLocation(country="CA", state="ON")
    db.session.add(test123_location)
    db.commit()


@app.route("/data/orgs", methods=["GET", "POST"])
def orgs_data():
    """TEST ROUTE TO GET ORGS DATA

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

    results = pf_api.petpy_api.organizations(
        country=country, state=state, sort="distance"
    )  # (**pf_api.default_options_obj)
    print([(org.name, org.adoption.policy) for org in results.organizations])
    # return jsonify(results)
    return render_template("results.html", results=results)


# Route to set & get API data in Flask Session
@app.route("/data/session", methods=["GET", "POST"])
def update_data_session():
    if request.method == "GET":
        if "api_data" in session:
            del session["api_data"]
            return jsonify(session["api_data"])
        return jsonify({})  # Return empty JSON if no data in session

    if request.method == "POST":
        api_data = request.args.get("api_data")
        if api_data:
            session["api_data"] = pf_api.parse_api_animals_data(api_data=api_data)
        else:
            return ValueError("No api data received")


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
    if "CURR_USER" in session:

        # check db, session and 'g' for user preferences. if not found, will return default country : 'CA', animal_type: 'dog'
        country = get_user_preference(key="country", session=session, g=g)
        animal_types = get_user_preference(key="animal_types", session=session, g=g)
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

    return render_template("users/form.html", form=form, next=url_for("data"))


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

            # init_orgs = pf_api.get_orgs_df()
        except IntegrityError:
            flash("Username already taken", "danger")
            db.session.rollback()
            return render_template("users/signup.html", form=form)

        do_login(user)

        # Redirect to user home
        return redirect(url_for("homepage"))

    else:

        db.session.rollback()
        return render_template("users/signup.html", form=form, next=True)


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


@app.route("/carousel", methods=["GET", "POST"])
def carousel_form_test():
    form = UserAddForm()

    return render_template("carousel-form.html", form=form)


@auth_required
@app.route("/users/preferences/<animal_type>", methods=["GET", "POST"])
def animal_preferences(animal_type):
    current_user_id = session.get("CURR_USER").get("id", None)
    if request.method == "GET":
        user_animal_prefs = UserAnimalPreferences.get_user_animal_pref_obj(
            u_id=current_user_id, animal_type=animal_type
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
                user_id=current_user_id,
                species=animal_type,
                form_data_obj=form.data,
            )
            print(new_prefs)
            flash(f"Successfully updated {animal_type} preferences.", "success")
            # return redirect(url_for("users_show", user_id=current_user_id))
            return redirect(url_for("animal_pref_data", animal_type=animal_type))
        except Exception as e:
            app.logger.error(f"Error updating preferences: {e}")
            db.session.rollback()
            flash(
                "An error occurred while saving your preferences. Please try again.",
                "danger",
            )
            return redirect(url_for("users_show", user_id=current_user_id))

    return render_template(
        "/users/user_animal_preferences.html", form=form, endpoint_param=animal_type
    )


##############################################################################
# Homepage and error pages


@app.route("/")
def homepage():
    """Show homepage:

    - anon users:
    - logged in:
    """

    if "CURR_USER_KEY" in session:
        # users_followed_by_current_user = g.user.following

        # Now, you can use this list of users to get their messages

        return render_template("home.html", user=g.user, messages=g.user.messages)

    else:
        # try:
        # params = {**pf_api.default_options_obj}
        # # results = pf_api.petpy_api.organizations(sort='-recent')#, country="CA", city="Toronto", state='ON')
        # results = pf_api.get_orgs_df(**params)
        # print(results)
        # except Exception as e:
        #     results = None

        return render_template("home-anon.html")  # , results=results


##############################################################################


# Initialize global variables before each request
@app.before_request
def get_app_data():
    """Function that runs before each request to refresh global variables and grab initial API data if none

    Returns:
        _type_: _description_
    """
    # update global variables
    with app.app_context():
        update_global_variables(session=session, g=g)
    # get JSON api_data from session
    # json_api_data = get_init_api_data(session=session, g=g)

    # # set api data in session via another route
    # requests.post(
    # url=url_for("update_data_session", _external=True),
    # data={"api_data": json_api_data, "headers": "application/json"},
    # )


# Inject context into Jinja templates to ensure that Flask session and 'g' object is available without having to manually pass as param into every template
@app.context_processor
def inject_global_vars():
    """Injects the session and g objects into the Jinja2 template context"""
    # print('template context processor being called', session['CURR_USER'])
    return {"session": session, "g": g, "animal_emojis": pf_api.animal_emojis}


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
    app.run(
        use_reloader=True,
        host=os.environ.get("HOST", "localhost"),
        port=os.environ.get("PORT", 5000),
    )
