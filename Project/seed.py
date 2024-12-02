"""Seed database with sample data from CSV Files."""
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy.exc import ProgrammingError
from dotenv import load_dotenv
from csv import DictReader
import json
import os
import bcrypt
import sys
from pathlib import Path
from Project.core.app import app, db
from Project.models.users import (
    User,
    UserLocation,
)
from Project.utils.filemanager import FileManager

if __name__ == "__main__":

    # Add the project root directory to the Python path
    sys.path.insert(0, Path(os.path.abspath(os.path.dirname(__file__))))
    load_dotenv()

    def load_setup_json(
        target_file: str = "test_user.json",
        target_dir: str = "mock_data",
    ):
        pwd = Path(os.path.abspath(os.path.dirname(__file__)))

        rel_path = FileManager.get_relative_path_to_file(
            target_file=target_file, parent_dir=target_dir
        )
        if rel_path:
            # Construct the full path to the target file
            target_file_path = pwd / rel_path

            # Check if the file exists before attempting to open it
            if target_file_path.exists():
                with open(target_file_path, "r") as file:
                    return json.load(file)
            else:
                print(f"File not found: {target_file_path}")
                return None
        else:
            print(f"Relative path not found for {target_file} in {target_dir}")
            return None


    test_user = load_setup_json(
        target_file="test_user.json",
        target_dir="mock_data",
    )
    test_location = load_setup_json(
        target_file="geodbcities/city_details/toronto/gdc_toronto_details_parsed.json",
        target_dir="mock_data",
    )

    # create app context for db
    app.app_context().push()

    # drop and recreate all tables
    db.drop_all()
    db.create_all()


    if os.environ.get("FLASK_ENV") != "production":
        salt = bcrypt.gensalt()
        test_user.password = bcrypt(test_user.password.encode("utf-8"), salt)
        test123 = User.signup(**test_user)
        test123_location = UserLocation(
            country=test_location.get("country_code", "CA"),
            state=test_location.get("region_code", "ON"),
        )
        db.session.add(test123_location)
        db.session.commit()

    # with open('fake-user-generator/users.csv') as users:
    #     db.session.bulk_insert_mappings(User, DictReader(users))

    # NEED TO REWORK THE FOLLOWING GENERATORS

    # with open('fake-user-generator/messages.csv') as messages:
    #     db.session.bulk_insert_mappings(Message, DictReader(messages))

    # with open('fake-user-generator/follows.csv') as follows:
    #     db.session.bulk_insert_mappings(Follows, DictReader(follows))

