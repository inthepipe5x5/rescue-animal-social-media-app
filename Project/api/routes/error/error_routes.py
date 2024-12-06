from http.client import HTTPException
from flask import request, redirect, Blueprint, render_template, url_for
from dotenv import load_dotenv

from Project.core.methods import (
    map_error_to_dict,
)

load_dotenv()

error_bp = Blueprint("error", __name__, url_prefix="/error")


# ERROR routes ##############################################################################
@error_bp.errorhandler(HTTPException)
def http_error_handler(e):
    """Handles HTTP exceptions."""
    error_info = map_error_to_dict(e)
    return redirect_to_custom_error(error_info)


@error_bp.errorhandler(Exception)
def internal_error_handler(e):
    """Handles all other exceptions."""
    error_info = map_error_to_dict(e)
    return redirect_to_custom_error(error_info)


@error_bp.route("/")
def custom_error():
    """Route to display the error page."""
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


def redirect_to_custom_error(error_info):
    """Redirects to the error page with error details."""
    return redirect(
        url_for(
            "error.custom_error",
            error_title=error_info["error_title"],
            error_subtitle=error_info["error_subtitle"],
            error_message=error_info["error_message"],
            redirect_url=error_info["redirect_url"],
            redirect_text=error_info["redirect_text"],
        )
    )
