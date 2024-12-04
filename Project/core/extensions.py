from pathlib import Path
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.schema import DropConstraint, DropTable
from flask_marshmallow import Marshmallow
from flask_login import (
    LoginManager,
)
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from psycopg2 import ProgrammingError

bcrypt = Bcrypt()
csrf = CSRFProtect()
ma = Marshmallow()  # flask-marshmallow for validation & serialization
db = SQLAlchemy()  # flask-sqlalchemy
login_manager = LoginManager()  # flask-login manager


def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """
    db.init_app(app)
    migrate = Migrate(app=app, db=db, directory="migrations", compare_type=True)
    # Use the custom function to drop everything with cascade
    with app.app_context():
        drop_everything(db)
        db.create_all()
        return db, migrate
    # print(db.metadata.tables) #printing tables for debugging
    return db, migrate



def drop_everything(db):
    # Disable foreign key constraints
    db.session.execute(text("SET session_replication_role = 'replica';"))
    
    inspector = inspect(db.engine)
    
    # Collect all table names
    table_names = inspector.get_table_names()
    
    for table_name in table_names:
        # Drop the table
        db.session.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
    
    # Re-enable foreign key constraints
    db.session.execute(text("SET session_replication_role = 'origin';"))
    db.session.commit()



if __name__ == "__main__":
    from Project.core.app import app

    db, migrate = connect_db(app=app)
