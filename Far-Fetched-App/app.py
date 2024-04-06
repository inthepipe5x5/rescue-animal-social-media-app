from flask import Flask, render_template, request, flash, redirect, session, g, url_for

# from flask_font_awesome import FontAwesome
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import pdb  # MAKE SURE TO REMOVE IN PRODUCTION
import os

from models import (
    db,
    User,
    UserLocation,
    UserPreferences,
    UserAnimalPreferences,
    UserAnimalBehaviorPreferences,
    UserAnimalAppearancePreferences,
)
from forms import (
    UserAddForm,
    LoginForm,
    UserEditForm,
    MandatoryOnboardingForm,
    # userSearchOptionsPreferencesForm,
    UserAnimalBehaviorPreferences,
    SpecificAnimalAppearancePreferenceForm
)
from PetFinderAPI import pf_api


CURR_USER_KEY = os.environ.get("CURR_USER_KEY", "curr_user")
session["ANIMAL_TYPES"] = (
    []
)  # session[ANIMAL_TYPES] = python list of 6 possible values:  ‘dog’, ‘cat’, ‘rabbit’, ‘small-furry’, ‘horse’, ‘bird’, ‘scales-fins-other’, ‘barnyard’.

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
app_config_instance.config_app(app=app, obj=config[flask_env_type])

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


# @app.before_request
# def add_api_auth_token_to_g():
#     """Add auth token to g. Auth token lasts for an hour"""

#     g.auth_token = PetFinderPetPyAPI.get_authentication_token()


def add_user_animal_types_to_g():
    """Add the animal types preferred by the user to 'g'"""
    if ANIMAL_TYPES in session:
        # Get animal types selected by the user from the previous form submission
        session[ANIMAL_TYPES] = UserAnimalPreferences.get_or_404(
            UserAnimalPreferences.user_id == session[CURR_USER_KEY]
        )
    else:
        session[ANIMAL_TYPES] = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route("/signup", methods=["GET", "POST"])
def signup():
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
                location=form.location.data
            )
            db.session.commit()
            
            init_orgs = pf_api.get_init_df_of_animal_rescue_organizations(
            location=form.location.data, 
        )
        except IntegrityError:
            flash("Username already taken", "danger")
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

    # IMPLEMENT THIS
    if not CURR_USER_KEY in session:
        do_login()

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
                return redirect(url_for("users_show", user_id=logged_in_user.id))
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
@app.route("/options/new", methods=["GET", "POST"])
def new_mandatory_options():
    """Sign Up Route -> mandatory onboarding form of user preferences to sort content for users

    Returns:
        redirects to:
        - User details page (with API search content)
            OR
        - Additional user preference options
    """
    form = MandatoryOnboardingForm()


    if form.validate_on_submit():
        # Process form submission

        submitted_animal_types = form.animal_types.data
        session["ANIMAL_TYPES"] = submitted_animal_types
        # Create UserPreferences
        new_user_preferences = UserPreferences(user_id=g.user.id)
        db.session.add(new_user_preferences)
        db.session.commit()

        # If CURR_PREFERENCES is available, update it with the newly created UserPreferences
        if "CURR_PREFERENCES" in session:
            session["CURR_PREFERENCES"] = new_user_preferences

        # Create UserLocation
        new_user_location = UserLocation(
            user_id=g.user.id, user_preferences_id=new_user_preferences.id
        )
        db.session.add(new_user_location)
        db.session.commit()

        # Redirect to the next form or route
        return redirect(url_for("next_route"))

    return render_template("mandatory_options.html", form=form)

@app.route('/options/edit')
def edit_mandatory_options():
    
    if 'CURR_PREFERENCES' in session:
        pass
    else:
        return redirect(url_for('new_mandatory_options'))
    
    # Initialize form
    if g.user:
        saved_location_obj = UserLocation.query.filter_by(user_id=g.user.id).first()
        if saved_location_obj:
            curr_location = (
                saved_location_obj.postal_code
                or f"{saved_location_obj.country}, {saved_location_obj.state_province}"
            )
        else:
            curr_location = None  # Handle the case where user location is not found

        animal_types = session.get("ANIMAL_TYPES", [])
        form = MandatoryOnboardingForm(
            location=curr_location, animal_types=animal_types
        )
        return render_template('mandatory_options.html', form=form)
    else:
        return redirect(url_for('login')) #user is redirected to login as they do not have the right credentials

@app.route("/options/animal_preferences/<str:animal_type>", methods=["GET", "POST"])
def animal_preferences(animal_type):
    form = SpecificAnimalAppearancePreferenceForm()

    # Query the PetFinder API to get breeds based on the selected animal types
    breed_choices = pf_api.breeds(animal_type)

    # Populate breed choices in the form
    form.breeds_preference.choices = [
        (name, name.capitalize()) for name in breed_choices
    ]

    if form.validate_on_submit():
        # Process form submission
        existing_animal_preferences = 
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
        return render_template("home-anon.html")


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
    print(os.environ)
    app.run(debug=True, use_reloader=True)
