# User /login/logout/signup routes
import os
from flask import Blueprint, session, render_template, flash, redirect, url_for, g
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, UserEditForm, LoginForm, UserExperiencesForm
from models import db, User, UserLocation

auth_bp = Blueprint("auth", __name__, template_folder="templates", url_prefix="/auth")

CURR_USER_KEY = os.environ.get("CURR_USER_KEY")

##############################################################################
# User /login/logout routes


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@auth_bp.route("/login", methods=["GET", "POST"])
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


@auth_bp.route("/logout")
def logout():
    """Handle logout of user."""

    if not CURR_USER_KEY in session:
        do_login(g.user)

    do_logout()
    flash("logged out successfully")
    return redirect(url_for("login"))

# SIGN UP ROUTES    
##############################################################################
@auth_bp.route("/signup", methods=["GET"])
def signup():
    """Route to redirect any signup links that need to be updated
    TO BE REMOVED BEFORE PRODUCTION

    Returns:
        redirect to signup_user Flask Route.
    """
    return redirect(url_for("signup_user"))


@auth_bp.route("/signup/user", methods=["GET", "POST"])
def signup_user():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()
    if form.validate_on_submit():
        data = {field.name: field.data for field in form}
        try:

            user = User.signup(**data)
            db.session.add(user)
            db.session.commit()
            # save user location
            user_location = UserLocation(
                user_id=user.id, country=form.country.data, state=form.state.data
            )
            user.location.append(user_location)
            db.session.add(user_location)
            db.session.commit()

            # init_orgs = pf_api.get_orgs_df()
        except IntegrityError:
            flash("Username already taken", "danger")
            db.rollback()
            return render_template("users/signup.html", form=form)

        do_login(user)

        return redirect(url_for("signup_preferences"))

    else:
        return render_template("users/signup.html", form=form, next=True)


@auth_bp.route("/signup/preferences", methods=["GET", "POST"])
def signup_preferences():
    """Route to return form for user location (state + country), animal_types

    Returns:
        _type_: _description_
    """
    u_pref_form = UserExperiencesForm()

    if u_pref_form.validate_on_submit():
        # Process u_pref_form submission

        submitted_animal_types = u_pref_form.animal_types.data
        # save form data to g, flask sessions and database
        update_user_preferences(
            form=u_pref_form, session=session, user=g.user
        )  # pass in a current user

        # Redirect to user home
        return redirect(url_for("homepage"))

    return render_template("users/form.html", form=u_pref_form, next=False)

