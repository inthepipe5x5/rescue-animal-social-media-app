from http.client import HTTPException
from flask import (
    request,
    redirect,
    url_for,
    Blueprint,
    flash,
    render_template,
    session,
    jsonify,
)
from dotenv import load_dotenv
import os

from core import (
    login_required,
    db,
    current_user,
    active_authenticated_user,
    handle_error,
)
from models import User, UserFavorites, UserLocation, UserAnimalPreferences
from forms import (
    UserAddForm,
    LoginForm,
    UserEditForm,
    UserExperiencesForm,
    UserLocationForm,
    AnonExperiencesForm,
    SpecificAnimalPreferencesForm,
    HiddenForm,
    HiddenLocationForm,
    UserTravelForm,
)

load_dotenv()

error_bp = Blueprint("error", __name__, url_prefix="error")


# ERROR routes ##############################################################################


# Register the error handler for all HTTP exceptions
@error_bp.errorhandler(HTTPException)
def http_error_handler(e):
    return handle_error(e)


# Register a catch-all error handler for any other exceptions
@error_bp.errorhandler(Exception)
def internal_error_handler(e):
    return handle_error(e)


@error_bp.route("/error")
def custom_error():
    """Route to handle custom errors and redirects from other routes."""
    error_title = request.args.get("error_title", "Error")
    error_subtitle = request.args.get("error_subtitle", "Something went wrong")
    error_message = request.args.get("error_message", "An unexpected error occurred.")
    redirect_url = request.args.get("redirect_url", "/")
    redirect_text = request.args.get("redirect_text", "Return Home 🏡")

    return render_template(
        "error_page.html",
        error_title=error_title,
        error_subtitle=error_subtitle,
        error_message=error_message,
        redirect_url=redirect_url,
        redirect_text=redirect_text,
    )
