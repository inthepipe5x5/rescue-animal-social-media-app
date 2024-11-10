import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from db import db

if __name__ == "__main__":
    print("Flask app =", app)
    app.run()
    
    # create all db tables
    with app.app_context():
        db.create_all()