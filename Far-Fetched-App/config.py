import os
import app

    
#set sqla URI to 'DATABASE_URL' env var 
app.config['SQLALCHEMY_DATABASE_URI'] = (
os.environ.get('DATABASE_URL', 'postgresql:///ff-rescue-db'))

if os.environ['FLASK_ENV'] == 'testing':
    os.environ['TESTING'] = True
    os.environ['DEBUG'] = True
elif os.environ['FLASK_ENV'] == 'production':
    os.environ['TESTING'] = False
    os.environ['DEBUG'] = False
else:
    os.environ['TESTING'] = False
    os.environ['DEBUG'] = True


app_config_obj = {
        'TESTING': os.environ.get('TESTING', False),
        'SECRET_KEY':os.environ.get('SECRET_KEY', "SECRET KEY"),
        'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', 'postgresql:///ff-rescue-db'),
        'WTF_CSRF_ENABLED': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ECHO': False,
    }

if app.config['TESTING'] == False:
    #set env var 'DATABASE_URL' to non-testing db
    app_config_obj['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']

else: 
    app_config_obj['SQLALCHEMY_DATABASE_URI'] = os.environ['TEST_DATABASE_URL']

app.config.update(app_config_obj)