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
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    #session configs
    SESSION_REFRESH_EACH_REQUEST = False #set to false to ensure cookie is not refreshed on each request
    #session security configs
    SESSION_COOKIE_SECURE = True #set to True for HTTPS
    SESSION_COOKIE_HTTPONLY = True # prevent malicious scripts from accessing the session cookie on the client side.
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
