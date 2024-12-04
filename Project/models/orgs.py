from flask import json
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import Column, Integer, String, Boolean, JSON
from sqlalchemy.dialects.postgresql import JSONB

from Project.core.extensions import db

# from Project.models.common import SchemaDbModel
# from Project.schemas.orgs import OrgResponseSchema
# from Project.models.animals import Animal
from Project.models.common import MetaDataMixin, PetFinderProviderMixin, attach_listeners


# subclass for Organizations
# class Organization(SchemaDbModel, schema=OrganizationSchema):
#     __tablename__ = "organizations"
#     api_list_key = "organizations"

#     id = Column(String(50), primary_key=True)


class Organization(db.Model, PetFinderProviderMixin):
    """Rescue Organization db.Model
        
        
        PetFinderProviderMixin (_type_): PetFinder subclass of MetaDataMixin
    
    """

    __tablename__ = "organizations"

    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String)
    phone = db.Column(db.String)
    petfinder_url = db.Column(db.String)  # petfinder URL
    website = db.Column(db.Text)
    mission_statement = db.Column(db.Text)
    hours = db.Column(JSONB)
    adoption_policy = db.Column(db.Text)
    adoption_url = db.Column(db.Text)

    # Socials, photos, and media links
    photos = db.Column(JSONB)
    social_media = db.Column(JSONB)
    social_media = db.Column(JSONB)

    # Relationships
    animals = db.relationship("Animal", back_populates="organization", uselist=True)

# Call this function after all models are defined
attach_listeners()
