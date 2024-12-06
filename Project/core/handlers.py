#flask signals handler functions

from flask import redirect, url_for
from Project.core.methods import handle_error

def handle_http_error(sender, error, **kwargs):
    """Signal handler to redirect to the custom error page."""
    error_info = handle_error(error)
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
