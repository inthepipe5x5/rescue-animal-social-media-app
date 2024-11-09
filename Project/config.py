import os
import re
import logging
from flask_wtf.csrf import CSRFProtect
from logging.config import dictConfig
from dotenv import load_dotenv
from Project.schemas.data.users.models import db, connect_db
from flask_migrate import Migrate
from sqlalchemy.engine.url import URL

# Load environment variables from .env file
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
os.environ["APP_DIR"] = basedir


# custom formatter for Flask logger to log in different colors

class CustomFormatter(logging.Formatter):
    # Define color codes
    grey = "\x1b[38;21m"
    blue = "\x1b[34;21m"
    bold_blue = "\x1b[34;1m"
    green = "\x1b[32;21m"
    bold_green = "\x1b[32;1m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    # Define highlight codes
    green_highlight = "\x1b[42m"
    yellow_highlight = "\x1b[43m"
    red_highlight = "\x1b[41m"
    purple_highlight = "\x1b[45m"

    # Define the format
    format = (
        "%(levelname)s - %(name)s - (%(filename)s:%(lineno)d) - %(message)s"
    )

    FORMATS = {
        logging.DEBUG: green + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        formatted_message = formatter.format(record)

        # Highlight status codes
        formatted_message = re.sub(
            r'\b(200|201)\b',
            f'{self.green_highlight}\\1{self.reset}',
            formatted_message
        )
        formatted_message = re.sub(
            r'\b(401|404)\b',
            f'{self.yellow_highlight}\\1{self.reset}',
            formatted_message
        )
        formatted_message = re.sub(
            r'\b(500)\b',
            f'{self.red_highlight}\\1{self.reset}',
            formatted_message
        )

        # Highlight debugger PIN
        formatted_message = re.sub(
            r'(Debugger PIN: )(\d+-\d+-\d+-\d+-\d+)',
            f'\\1{self.purple_highlight}\\2{self.reset}',
            formatted_message
        )

        return formatted_message


class Config:
    # Default configuration
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    TESTING = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "SECRET KEY")
    # hardcoding in the postgresql DB for now as the URI is not being set as an env variable properly
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # set to None to disable expiration
    CSRF_ENABLED = True
    # SQLALCHEMY_DATABASE_URI =  os.environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="postgresql",
        username=os.environ.get("SUPABASE_USER"),
        password=os.environ.get("SUPABASE_PW"),
        host=os.environ.get("SUPABASE_HOST"),
        database="postgres",
        port=5432,
        # sslmode="require",
    )  # os.environ.get('SQLALCHEMY_DATABASE_URI') #if not SUPABASE_URI else SUPABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = (
        False  # set to true to debug db logs; else False to not flood terminal
    )

    # session configs
    SESSION_REFRESH_EACH_REQUEST = (
        False  # set to false to ensure cookie is not refreshed on each request
    )
    #keep session permanent to try fixing session resetting issues
    SESSION_PERMANENT=True
    # session security configs
    SESSION_COOKIE_SECURE = True  # set to True for HTTPS
    SESSION_COOKIE_HTTPONLY = True  # prevent malicious scripts from accessing the session cookie on the client side.

    @staticmethod
    def get_logger_config():
        return {
            "version": 1,
            "formatters": {
                "default": {
                    "()": CustomFormatter  # Use the custom formatter defined above
                }
            },
            "handlers": {
                "wsgi": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "default",
                }
            },
            "root": {
                "level": "DEBUG",  # Default to DEBUG for non-prod configs
                "handlers": ["wsgi"],
            },
        }

    @staticmethod
    def config_app(app, obj):
        """
        If some configuration needs to config the app in some way use this function
        :param app: Flask app, update object
        :return:
        """

        app.config.from_object(obj)

        # Configure logging
        dictConfig(obj.get_logger_config())

        connect_db(app)

        migrate = Migrate(app, db, compare_type=True)

        # enable CSRF globally
        csrf = CSRFProtect()
        csrf.init_app(app)
        return app


class DevelopmentConfig(Config):
    DEBUG = True
    EXPLAIN_TEMPLATE_LOADING = True

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False  # disable this for testing purposes
    EXPLAIN_TEMPLATE_LOADING = True
    CSRF_ENABLED = False
    # hardcoding in the postgresql DB for now as the URI is not being set as an env variable properly
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_TEST_DATABASE_URI")


class ProductionConfig(Config):
    DEBUG = False
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_PROD_DATABASE_URI")
    SQLALCHEMY_ECHO = False  # set to False for prod

    # override the inherited .init_app() from parent Config() class
    @staticmethod
    def config_app(app, obj):
        """
        If some configuration needs to config the app in some way use this function
        :param app: Flask app, update object
        :return:
        """

        app.config.from_object(obj)

        # Configure logging
        dictConfig(obj.get_logger_config())

        connect_db(app)
        migrate = Migrate(app, db, compare_type=True)

        return app

    # override the inherited .get_logger_config() from parent Config() class
    @staticmethod
    def get_logger_config():
        config = Config.get_logger_config()
        config["root"]["level"] = "INFO"  # Set to INFO for production
        return config


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
