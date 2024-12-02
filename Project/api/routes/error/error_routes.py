from http.client import HTTPException
from flask import (
    request,
    redirect,
    url_for,
    Blueprint,
    render_template,
)
from dotenv import load_dotenv

from Project.core import (
    
    handle_error,
    default_error_details,
)

load_dotenv()

error_bp = Blueprint(
    "error", __name__, url_prefix="error", url_defaults=url_for("error")
)


# ERROR routes ##############################################################################


# Register the error handler for all HTTP exceptions
@error_bp.errorhandler(HTTPException)
def http_error_handler(e):
    return handle_error(e)


# Register a catch-all error handler for any other exceptions
@error_bp.errorhandler(Exception)
def internal_error_handler(e):
    error_info = handle_error(e)
    return (
        redirect(
            "error",
            error_title=error_info["error_title"],
            error_subtitle=error_info["error_subtitle"],
            error_message=error_info["error_message"],
            redirect_url=error_info.get(
                "redirect_url", default_error_details["redirect_url"]
            ),
            redirect_text=error_info.get(
                "redirect_text", default_error_details["redirect_text"]
            ),
        ),
        e.status_code,
    )


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
