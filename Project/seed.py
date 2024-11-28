"""Seed database with sample data from CSV Files."""

from csv import DictReader
import json
from Project.core.app import app, db
from Project.models.users import (
    User,
    UserLocation,
    UserAnimalPreferences,
    MatchedRescueOrganization,
    db,
)
import os
import bcrypt

file_path = os.path.join(os.getcwd(), "tests/test_user.json")
with open(file_path, "r") as file:
    test_user = json.load(file)

# create app context for db
app.app_context().push()

# drop and recreate all tables
db.drop_all()
db.create_all()


if os.environ.get("FLASK_ENV") != "production":
    salt = bcrypt.gensalt()
    test_user.password = bcrypt(test_user.password.encode("utf-8"), salt)
    test123 = User.signup(**test_user)
    test123_location = UserLocation(country="CA", state="ON")
    db.session.add(test123_location)

# with open('fake-user-generator/users.csv') as users:
#     db.session.bulk_insert_mappings(User, DictReader(users))

# NEED TO REWORK THE FOLLOWING GENERATORS

# with open('fake-user-generator/messages.csv') as messages:
#     db.session.bulk_insert_mappings(Message, DictReader(messages))

# with open('fake-user-generator/follows.csv') as follows:
#     db.session.bulk_insert_mappings(Follows, DictReader(follows))

db.session.commit()
