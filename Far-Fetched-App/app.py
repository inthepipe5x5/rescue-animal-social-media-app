from flask import (
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

# from flask_font_awesome import FontAwesome
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import pdb  # MAKE SURE TO REMOVE IN PRODUCTION
import os

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
    MandatoryOnboardingForm,
    UserLocationForm,
    # userSearchOptionsPreferencesForm,
    # UserAnimalBehaviorPreferences,
    SpecificAnimalPreferencesForm,
)
from PetFinderAPI import pf_api  # PetFinderPetPyAPI

# pf_api = PetFinderPetPyAPI()


CURR_USER_KEY = os.environ.get("CURR_USER_KEY", "curr_user")

# RESOLVE THIS: commented out font_awesome as there an import error to be resolved
# font_awesome = FontAwesome(app)
from config import config, Config

load_dotenv()


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

# set default saved user_preferences
# session["user_preferences"] = pf_api.default_options_obj

# create API wrapper class instance
# pet_finder_API = pf_api

##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get_or_404(session[CURR_USER_KEY])
    else:
        g.user = None


# def add_user_animal_types_to_g():
#     """Add the animal types preferred by the user to 'g'"""
#     if 'ANIMAL_TYPES' in session:
#         # Get animal types selected by the user from the previous form submission
#         session['ANIMAL_TYPES'] = UserAnimalPreferences.get_or_404(
#             UserAnimalPreferences.user_id == session[CURR_USER_KEY]
#         )
#     else:
#         session['ANIMAL_TYPES'] = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route("/signup/user", methods=["GET", "POST"])
def signup_user():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()
    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
                location=form.location.data,
                bio=form.bio.data,
            )
            db.session.add(user)
            db.session.commit()

            # init_orgs = pf_api.get_orgs_df()
        except IntegrityError:
            flash("Username already taken", "danger")
            db.rollback()
            return render_template("users/signup.html", form=form)

        do_login(user)

        return redirect(url_for("mandatory_options"))

    else:
        return render_template("users/signup.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", "danger")

    return render_template("users/login.html", form=form)


@app.route("/logout")
def logout():
    """Handle logout of user."""

    if not CURR_USER_KEY in session:
        do_login(g.user)

    do_logout()
    flash("logged out successfully")
    return redirect(url_for("login"))


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


@app.route("/users/<int:user_id>/following")
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template("users/following.html", user=user)


@app.route("/users/<int:user_id>/followers")
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template("users/followers.html", user=user)


@app.route("/users/follow/<int:follow_id>", methods=["POST"])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route("/users/stop-following/<int:follow_id>", methods=["POST"])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route("/users/profile", methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect(url_for("login"))

    else:
        logged_in_user = User.query.get(g.user.id)
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

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Route to get updated API data
@app.route("/get_data_results_in_session", methods=["GET"])
def get_data_results_in_session():
    if "api_data" in session:
        return jsonify(session["api_data"])
    return jsonify({})  # Return empty JSON if no data in session


# Route to handle form submissions and API calls
@app.route("/submit_section", methods=["POST"])
def submit_section():
    section_data = request.form
    # Make API call using section_data
    mapped_preferences_data = pf_api.map_user_form_data(section_data)
    api_data = pf_api.petpy_api.animals(mapped_preferences_data)
    # Store API data in session
    session["api_data"] = api_data
    return "API data received"


##############################################################################
@app.route("/signup", methods=["GET"])
def signup():
    return redirect(url_for("signup_preferences"))


@app.route("/signup/preferences", methods=["GET", "POST"])
def signup_preferences():
    u_pref_form = MandatoryOnboardingForm()

    if u_pref_form.validate_on_submit():
        # Process u_pref_form submission

        submitted_animal_types = u_pref_form.animal_types.data
        rescue_action_type = u_pref_form.rescue_action_type.data

        if "user_preferences" in session:
            session["user_preferences"]["animal_types"] = submitted_animal_types
        else:
            session["user_preferences"] = pf_api.default_options_obj
            session["user_preferences"]["animal_types"] = submitted_animal_types

        session["rescue_action_type"] = rescue_action_type
        # print(session['animal_types'])
        # print(session['rescue_action_type'])
        print(submitted_animal_types, rescue_action_type)
        # Create new user
        new_user = User(rescue_action_type=rescue_action_type)

        db.session.add(new_user)
        db.session.commit()

        # Redirect to the next u_pref_form or route
        return redirect(url_for("signup_location"))

    return render_template("users/form.html", form=u_pref_form, next=True)


@app.route("/signup/location", methods=["GET", "POST"])  # type: ignore
def signup_location():
    """Sign Up Route -> mandatory onboarding form of user preferences to sort content for users

    Returns:
        redirects to:
        - User details page (with API search content)
            OR
        - Additional user preference options
    """

    u_location_form = UserLocationForm()

    if u_location_form.validate_on_submit():
        data = u_location_form.data
        mapped_data = pf_api.map_user_form_data(form_data=data)
        mapped_location = mapped_data["location"]

        # Check if user has an existing location
        existing_location = UserLocation.query.filter_by(user_id=g.user.id).first()

        if existing_location:
            # Update existing location
            existing_location.populate_by_obj(mapped_location)
        else:
            # Create new location
            new_user_location = UserLocation(
                user_id=g.user.id,
                country=mapped_location["country"],
                state=mapped_location["state"],
                city=mapped_location["city"],
            )  # type: ignore
            db.session.add(new_user_location)

        # update the preferences in session
        session["user_preferences"] = {**mapped_data, **session["user_preferences"]}

        # commit changes to db
        db.session.commit()
        return redirect(url_for("signup_user"))
    else:
        return render_template("users/form.html", form=u_location_form, next=True)


@app.route("/carousel", methods=["GET", "POST"])
def carousel_form_test():
    form = UserAddForm()

    return render_template("carousel-form.html", form=form)


@app.route("/options/animal_preferences/<animal_type>", methods=["GET", "POST"])
def animal_preferences(animal_type):
    form = SpecificAnimalPreferencesForm()

    # Query the PetFinder API to get breeds based on the selected animal types
    breed_choices = pf_api.breeds(animal_type)
    if breed_choices:
        print(breed_choices)
        # Populate breed choices in the form
        form.AppearancePreferencesSection.breeds.choices = [
            (name, name.capitalize()) for name in breed_choices
        ]
    coat_color_choices = pf_api.animal_types(animal_type).coat
    if coat_color_choices:
        form.AppearancePreferencesSection.color.choices = [
            (name, name.capitalize()) for name in coat_color_choices
        ]

    if form.validate_on_submit():
        # Process form submission
        existing_animal_preferences = animal_preferences.query.get_or_404()
        form.populate_obj(existing_animal_preferences)

        # Redirect to the next form or route
        return redirect(url_for("next_route"))

    return render_template("animal_preferences.html", form=form)


##############################################################################
# Homepage and error pages


@app.route("/")
def homepage():
    """Show homepage:

    - anon users:
    - logged in:
    """

    if g.user:
        users_followed_by_current_user = g.user.following

        # Now, you can use this list of users to get their messages

        return render_template("home.html")

    else:
        try:
            params = {**pf_api.default_options_obj}
            # results = pf_api.petpy_api.organizations(sort='-recent')#, country="CA", city="Toronto", state='ON')
            results=pf_api.get_orgs_df(**params)
            print(results)
        except Exception as e:
            results = None
        animal_emojis = {
            "dog": "🐶",
            "cat": "🐱",
            "rabbit": "🐰",
            "small-furry": "🐹",
            "horse": "🐴",
            "bird": "🐦",
            "scales-fins-other": "🦎",
            "barnyard": "🐄",
        }
        return render_template(
            "results.html", results=results, animal_emojis=animal_emojis
        )


##############################################################################
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
    app.run(debug=True, use_reloader=True)
