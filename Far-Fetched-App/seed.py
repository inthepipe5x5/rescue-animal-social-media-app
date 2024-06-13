"""Seed database with sample data from CSV Files."""

from csv import DictReader
from app import app, db
from models import User, UserAnimalPreferences, MatchedRescueOrganization

# create app context for db
app.app_context().push()

# drop and recreate all tables
db.drop_all()
db.create_all()

# with open('fake-user-generator/users.csv') as users:
#     db.session.bulk_insert_mappings(User, DictReader(users))

#NEED TO REWORK THE FOLLOWING GENERATORS
    
# with open('fake-user-generator/messages.csv') as messages:
#     db.session.bulk_insert_mappings(Message, DictReader(messages))

# with open('fake-user-generator/follows.csv') as follows:
#     db.session.bulk_insert_mappings(Follows, DictReader(follows))

db.session.commit()
