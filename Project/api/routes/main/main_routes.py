import os
from flask import Blueprint, render_template, url_for
from flask_login import current_user

from Project.core.methods import (
    active_authenticated_user,
    load_session,
)
from Project.forms import (
    UserExperiencesForm,
)

main_bp = Blueprint(
    "main",
    __name__,
)


# Homepage and error pages
@main_bp.route("/")
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
