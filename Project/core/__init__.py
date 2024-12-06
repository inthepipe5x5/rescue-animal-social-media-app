# from Project.core.constants import *
import os

# from Project.types import *
from flask import Flask, before_render_template
from Project.api.signals.handlers import inject_global_vars, add_header
from Project.config import Config, config
from Project.utils.parse import Parse

from Project.core.extensions import (
    connect_db,
    ma,
    login_manager,
    bcrypt,
    csrf,
)


def create_app():
    # create app with factory method
    app = Flask(
        __name__, template_folder="Project/templates", static_folder="Project/static"
    )

    # CONFIG APP
    # create config instance
    app_config_instance = Config()
    # Grab FLASK_ENV from environment variables
    flask_env_type = os.environ.get("FLASK_ENV", "default")
    app_config_instance.config_app(app=app, obj=config[flask_env_type])
    
    # Inject global variables into Jinja context before rendering templates
    before_render_template.connect(inject_global_vars, app)

    @app.after_request
    def post_request_processing(req):
        return add_header(sender=post_request_processing, req=req)

    # Register blueprints before extensions and return app afterwards
    from Project.api import register_bp
    app = register_bp(app)


    # INITIALIZE EXTENSIONS
    # Set up DB & Flask-Migrate
    db, migrate = connect_db(app)
    csrf.init_app(app)
    bcrypt.init_app(app)
    ma.init_app(app)
    login_manager.init_app(app)

    # config flask-login.login manager
    login_manager.login_view = "auth_bp.login"

    # user load function to load user session based on user_id
    @login_manager.user_loader
    def load_user(user_id):
        from Project.models import User

        return User.query.get(int(user_id))

    # Inject Custom Jinja filters Here
    custom_filters_dict = {
        "format_kebob_case": Parse.format_kebob_case,
        "prettify_animal_types": Parse.prettify_animal_types,
    }
    for function_key, function in custom_filters_dict.items():
        app.jinja_env.filters[function_key] = function

    # Debugging block
    if os.environ.get("FLASK_ENV") != "production":
        try:
            assert app.template_folder  # Check if template folder is properly set
            assert app.static_folder  # Check if static folder is properly set
        except AssertionError as e:
            app.logger.error(
                f"App template/static folders not set properly: {e}. "
                f"template_folder: {app.template_folder}, static_folder: {app.static_folder}"
            )

    return app


if __name__ == "__main__":
    pass
