#flask signals handler functions

from flask import redirect, url_for, current_app
from Project.core.methods import map_error_to_dict

def handle_http_error(sender, error, **kwargs):
    """Signal handler to redirect to the custom error page."""
    
    sender = sender if sender else current_app._get_current_object() #default to Flask.current_app as sender
    
    error_info = map_error_to_dict(error)
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
