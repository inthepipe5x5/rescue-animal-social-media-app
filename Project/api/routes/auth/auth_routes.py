# auth/routes.py
import os
from flask import Blueprint, flash, redirect, session, g, render_template
from flask_login import login_required
from dotenv import load_dotenv
from Project.core.methods import do_login, do_logout, init_default_session
from Project.models import User
from Project.forms import LoginForm

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
)

load_dotenv()
CURR_USER_KEY = os.environ.get("CURR_USER_KEY", "curr_user")


##############################################################################
# User signup/login/logout


@auth_bp.route("/login", methods=["GET", "POST"])
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
@auth_bp.route("/logout")
def logout():
    """Handle logout of user."""
    # remove user from session
    do_logout()
    # populate default session data in
    init_default_session()
    flash(f"Log out successful. Hope to see you again", "success")
    return redirect("/")
