from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask.sessions import (
    SessionInterface,
    SessionMixin,
    NullSession,
)
from flask_login import (
    LoginManager,
    login_required,
    login_user,
    logout_user,
    current_user,
)

from app import app
from models import User

ma = Marshmallow()
db = SQLAlchemy()

# config bcrypt
bcrypt = Bcrypt(app)

# config flask-login.login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# user load function to load user session based on user_id
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


if __name__ == "__main__":
    from app import app

    with app.app_context():
        db.create_all()
