# auth/routes.py
import os
from flask import Blueprint, flash, redirect, session, g, render_template, url_for
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from models import db, User
from forms import LoginForm, UserAddForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

load_dotenv()
CURR_USER_KEY = os.environ.get("CURR_USER_KEY", 'curr_user')


##############################################################################
# User signup/login/logout


@auth_bp.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get_or_404(session[CURR_USER_KEY])
    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@auth_bp.route('/signup', methods=["GET", "POST"])
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
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@auth_bp.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@auth_bp.route('/logout')
def logout():
    """Handle logout of user."""

    # IMPLEMENT THIS
    if not CURR_USER_KEY in session:
        do_login()
    
    do_logout()
    flash('logged out successfully')
    return redirect(url_for('login'))
