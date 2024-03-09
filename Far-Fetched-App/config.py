import os
from dotenv import load_dotenv
from models import connect_db

# Load environment variables from .env file
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

print(os.environ.get('FLASK_ENV','FLASK_APP'))
class Config:
    # Default configuration
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', "SECRET KEY")
    # hardcoding in the postgresql DB for now as the URI is not being set as an env variable properly
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI', 'postgresql:///ff-rescue-db')
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    @staticmethod
    def config_app(app, obj):
        """
        If some configuration needs to config the app in some way use this function
        :param app: Flask app, update object
        :return:
        """
        
        app.config.from_object(obj)
        connect_db(app)
        
        return app

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    # hardcoding in the postgresql DB for now as the URI is not being set as an env variable properly
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_TEST_DATABASE_URI', 'postgresql:///ff-rescue-db-test')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_PROD_DATABASE_URI')

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
