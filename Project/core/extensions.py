from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_login import (
    LoginManager,
)
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

csrf = CSRFProtect()
ma = Marshmallow()  # flask-marshmallow for validation & serialization
db = SQLAlchemy()  # flask-sqlalchemy
login_manager = LoginManager()  # flask-login manager
bcrypt = Bcrypt()


def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.init_app(app)
    migrate = Migrate(app=app, db=db, directory="migrations", compare_type=True)
    return db, migrate

if __name__ == "__main__":
    from Project.core.app import app

    with app.app_context():
        db.create_all()
