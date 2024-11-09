"""Seed database with sample data from CSV Files."""

from csv import DictReader
from app import app, db
from Project.schemas.data.users.models import (
    User,
    UserLocation,
    UserAnimalPreferences,
    MatchedRescueOrganization,
    db,
)
import os
import bcrypt

test_user = {
    "username": "test123",
    "email": "test123@test123.com",
    "bio": "test123",
    "password": "test123",
    "animal_types": ["dog"],
    "image_url": "../static/images/profile-images/default-hero-sasha-sashina-YCsh4ltV9Ec-unsplash.jpg",
    "rescue_action_type": ["volunteering", "donation", "adoption", "animal foster"],
}

# create app context for db
app.app_context().push()

# drop and recreate all tables
db.drop_all()
db.create_all()


if os.environ.get("FLASK_ENV") != "production":
    salt = bcrypt.gensalt()
    test_user.password = bcrypt(test_user.password.encode('utf-8'), salt)
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
