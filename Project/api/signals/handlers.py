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

def inject_global_vars(sender, template, context, **extra):
    """Injects the key app values into the Jinja2 template context"""
    from flask import g, session
    from flask_login import current_user
    from Project.core.constants import default_animal_types, animal_emojis, animal_colors, default_animal_photos
    from Project.core.methods import active_authenticated_user
    from Project.utils.parse import Parse
    
    app = current_app._get_current_object()
    
    app.logger.debug("Injecting global variables into template context")
    context.update({
        "session": session,
        "g": g,
        "animal_types": default_animal_types,
        "animal_emojis": animal_emojis,
        "animal_colors": animal_colors,
        "animal_default_photos": default_animal_photos,
        "animal_border_colors": {
            key: "border-" + value for key, value in animal_colors.items()
        },
        "animal_bg_colors": {
            key: "bg-" + value for key, value in animal_colors.items()
        },
        "animal_btn_colors": {
            key: "btn-" + value for key, value in animal_colors.items()
        },
        "CURR_USER": (
            current_user._get_current_object()
            if (active_authenticated_user() and current_user)
            else None
        ),
        "user_auth_status": active_authenticated_user(),
        "default_prettified_animal_types": Parse.get_default_prettified_animal_types,
    })

def add_header(sender, req, **kwargs):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers["Cache-Control"] = "public, max-age=0"
    return req