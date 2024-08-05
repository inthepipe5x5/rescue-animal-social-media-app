import os
import logging
from logging.config import dictConfig
from dotenv import load_dotenv
from models import connect_db

# Load environment variables from .env file
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
os.environ['APP_DIR'] = basedir

#custom formatter for Flask logger to log in different colors
class CustomFormatter(logging.Formatter):
    # Define color codes
    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    # Define the format: time - logger name - levelname/severity - log message content - filename/logging source - line # of logging call
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    
    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
    
class Config:
    # Default configuration
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', "SECRET KEY")
    # hardcoding in the postgresql DB for now as the URI is not being set as an env variable properly
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False #set to true to debug db logs; else False to not flood terminal
    
    #session configs
    SESSION_REFRESH_EACH_REQUEST = False #set to false to ensure cookie is not refreshed on each request
    #session security configs
    SESSION_COOKIE_SECURE = True #set to True for HTTPS
    SESSION_COOKIE_HTTPONLY = True # prevent malicious scripts from accessing the session cookie on the client side.
    @staticmethod
    def get_logger_config():
        return {
            'version': 1,
            'formatters': {
                'default': {
                    '()': CustomFormatter  # Use the custom formatter defined above
                }
            },
            'handlers': {
                'wsgi': {
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stdout',
                    'formatter': 'default'
                }
            },
            'root': {
                'level': 'DEBUG',  # Default to DEBUG for non-prod configs
                'handlers': ['wsgi']
            }
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
        
        return app

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    # hardcoding in the postgresql DB for now as the URI is not being set as an env variable properly
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_TEST_DATABASE_URI')

class ProductionConfig(Config):
    DEBUG = False
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_PROD_DATABASE_URI')
    SQLALCHEMY_ECHO = False  # set to False for prod

    #override the inherited .get_logger_config() from parent Config() class
    @staticmethod
    def get_logger_config():
        config = Config.get_logger_config()
        config['root']['level'] = 'INFO'  # Set to INFO for production
        return config

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
