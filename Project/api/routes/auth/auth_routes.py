# auth/routes.py
import os
from flask import Blueprint, flash, redirect, session, g, render_template
from flask_login import login_required, user_login_confirmed
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

# Signal handler for successful login
@user_login_confirmed.connect
def handle_successful_login(sender, user, **kwargs):
    """This function is triggered when the user_login_confirmed signal is sent."""
    # Log the user in
    do_login(user)
    
    # Store user object in the global context
    g.user = user
    
    # Store the serialized user object in the session
    session["CURR_USER"] = user.serialize()
    print(g.user)


# Login route
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    form = LoginForm()

    if form.validate_on_submit():
        # Authenticate the user
        user = User.authenticate(form.username.data, form.password.data)

        if user:
            # Send the user-login-confirmed signal if authentication is successful
            user_login_confirmed.send(auth_bp, user=user)
            
            # Flash success message and redirect
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        # If authentication fails, flash an error message
        flash("Invalid credentials.", "danger")

    # If the form is not submitted or invalid, render the login page
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
