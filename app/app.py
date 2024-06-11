import dotenv
from flask import Flask, Blueprint, render_template, request, flash, redirect, session, g, url_for
import os

from models import db, User
from dotenv import load_dotenv
# from __init__ import app
from config import config, Config

from app.main.routes import main
from app.auth.routes import auth
from app.users.routes import users

#set env variables
CURR_USER_KEY = os.environ.get("CURR_USER_KEY", 'curr_user')
load_dotenv()

def create_app():
    # create Flask app
    app = Flask(__name__)

    # create config instance
    app_config_instance = Config()

    # config Flask app
    flask_env_type = (
        os.environ.get("FLASK_ENV")
        if os.environ.get("FLASK_ENV") is not None
        else "default"
    )
    app_config_instance.config_app(app=app, obj=config[flask_env_type])

    # register blueprints
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(users)
    return app


app = create_app()

##############################################################################
@app.route('/')
def homepage():
    """Show homepage:

    - anon users:
    - logged in: 
    """

    if g.user:
        # users_followed_by_current_user = g.user.following

        # Now, you can use this list of users to get their messages


        return render_template('home.html')

    else:
        return render_template('home-anon.html')
##############################################################################



# Inject context into Jinja templates to ensure that Flask session and 'g' object is available without having to manually pass as param into every template
@app.context_processor
def inject_global_vars():
    """Injects the session and g objects into the Jinja2 template context"""
    return {"session": session, "g": g}


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
