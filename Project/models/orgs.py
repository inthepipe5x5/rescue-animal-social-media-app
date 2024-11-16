from sqlalchemy import Column, Integer, String, Boolean, JSON
from sqlalchemy.dialects.postgresql import JSONB

from Project.common import SchemaDbModel
from Project..schemas.orgs import OrganizationSchema
from core import db, ma


# subclass for Organizations
class Organization(SchemaDbModel, schema=OrganizationSchema):
    __tablename__ = "organizations"
    api_list_key = "organizations"

    id = Column(String(50), primary_key=True)

#TODO: remove? 
# class Organization(db.Model):
#     id = db.Column(db.String, primary_key=True)
#     name = db.Column(db.String, nullable=False)
#     email = db.Column(db.String)
#     phone = db.Column(db.String)
#     url = db.Column(db.String)
#     website = db.Column(db.String)
#     mission_statement = db.Column(db.Text)
#     distance = db.Column(db.Float)


# class Address(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     organization_id = db.Column(db.String, db.ForeignKey("organization.id"))
#     address1 = db.Column(db.String)
#     address2 = db.Column(db.String)
#     city = db.Column(db.String)
#     state = db.Column(db.String)
#     postcode = db.Column(db.String)
#     country = db.Column(db.String)


# TODO: either make this a property OR move to schemas.orgs

# class OrganizationSchema(ma.SQLAlchemySchema):
#     class Meta:
#         model = Organization
#         include_fk = True
#         include_relationships = True
#         load_instance = True
