# Homepage and error pages
import os
from flask import Blueprint, flash, redirect, session, g, render_template, url_for, request
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from ..models import db, User
from ..forms import UserEditForm
from ..auth.routes import do_logout

main_bp = Blueprint('main', __name__, template_folder='templates', url_prefix='/main')

load_dotenv()
CURR_USER_KEY = os.environ.get("CURR_USER_KEY", 'curr_user')



@main_bp.route('/')
def homepage():
    """Show homepage:

    - anon users:
    - logged in: 
    """

    if g.user:
        users_followed_by_current_user = g.user.following

        # Now, you can use this list of users to get their messages


        return render_template('home.html')

    else:
        return render_template('home-anon.html')

