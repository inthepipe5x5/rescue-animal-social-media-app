import os
from dotenv import load_dotenv
from models import connect_db

# Load environment variables from .env file
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
os.environ['APP_DIR'] = basedir

class Config:
    # Default configuration
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', "SECRET KEY")
    # hardcoding in the postgresql DB for now as the URI is not being set as an env variable properly
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_PATH='/'

    @staticmethod
    def config_app(app, obj):
        """
        If some configuration needs to config the app in some way use this function
        :param app: Flask app, update object
        :return:
        """
        
        app.config.from_object(obj)
        
        # app.config.from_envvar(os.environ.get('PWD'+'/.env', basedir))
        connect_db(app)
        
        return app

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    # hardcoding in the postgresql DB for now as the URI is not being set as an env variable properly
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_TEST_DATABASE_URI')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_PROD_DATABASE_URI')

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
