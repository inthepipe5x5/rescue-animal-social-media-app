# from Project.core.constants import *
import os

# from Project.types import *
from flask import Flask
from Project.config import Config, config
from Project.core.extensions import (
    connect_db,
    ma,
    login_manager,
    bcrypt,
    csrf,
)

# from Project.core.app import app


from flask_migrate import Migrate


def create_app():
    # create app with factory method
    app = Flask(__name__)

    # CONFIG APP
    # create config instance
    app_config_instance = Config()

    # config Flask app
    flask_env_type = (
        os.environ.get("FLASK_ENV")
        if os.environ.get("FLASK_ENV") is not None
        else "default"
    )
    app_config_instance.config_app(app=app, obj=config[flask_env_type])

    # Register blueprints before extensions
    from Project.api import register_bp

    register_bp(app)

    # Config app

    # INITIALIZE EXTENSIONS
    # Set up DB & Flask-Migrate
    db, migrate = connect_db(app)
    csrf.init_app(app)
    bcrypt(app)
    ma.init_app(app)
    login_manager.init_app(app)

    # config flask-login.login manager
    login_manager.login_view = "login"

    # user load function to load user session based on user_id
    @login_manager.user_loader
    def load_user(user_id):
        from models import User

        return User.query.get(int(user_id))

    return app


if __name__ == "__main__":
    pass
