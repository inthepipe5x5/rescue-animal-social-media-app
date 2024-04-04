"""SQLAlchemy models for app."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()


class Follows(db.Model):
    """Connection of a follower <-> followed_user."""

    __tablename__ = "follows"

    user_being_followed_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="cascade"),
        primary_key=True,
    )

    user_following_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="cascade"),
        primary_key=True,
    )


class RescueOrganization(db.Model):
    """Rescue Organization db.Model

    Args:
        db (_type_): _description_

    Returns:
        _type_: _description_
    """

    __tablename__ = "rescueOrg"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    location_id = db.Column(
        db.Integer,
        db.ForeignKey("location.id", ondelete="cascade"),
        primary_key=True,
    )


class User(db.Model):
    """User in the system."""

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    email = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    username = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    image_url = db.Column(
        db.Text,
        default="/static/images/profile-images/default-hero-sasha-sashina-YCsh4ltV9Ec-unsplash.jpg",
    )

    header_image_url = db.Column(
        db.Text,
        default="/static/images/profile-images/default-header-image-natalie-kinnear-MUkxOfl8epk-unsplash.jpg",
    )

    bio = db.Column(db.Text)

    location = db.Column(db.String(80))
    # user_residence = db.relationship("user_residence", back_populates="user")

    password = db.Column(
        db.Text,
        nullable=False,
    )
    registration_date = db.Column(db.DateTime)

    # animal_handling_experience = db.Column(
    #     db.String,
    #     db.ForeignKey("user_animal_handling_history.animal_handling_experience"),
    # )
    # matched_agencies = db.relationship("UserMatchedAgencies", back_populates="user")
    # followed_agencies = db.relationship("FollowedAgencies", back_populates="user")
    # user_reviews = db.relationship("UserReviews", back_populates="user")

    following = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follows.user_following_id == id),
        overlaps="followers",
        secondaryjoin=(Follows.user_being_followed_id == id),
    )

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}, {self.bio}, {self.location}>"

    def is_following(self, other_user):
        """Is this user following any rescue agencies?"""

        found_user_list = [user for user in self.following if user == other_user]
        return len(found_user_list) == 1

    @classmethod
    def signup(cls, username, email, password, image_url):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode("utf8")

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
            image_url=image_url,
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False

class UserPreferences(db.Model):
    """Relational table that stores id of the other preferences tables associated with one User"""

    __tablename__ = "user_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    user_location_id = db.Column(db.Integer, db.ForeignKey("user_location.id"))
    rescue_interaction_type_preference = db.Column(db.ARRAY(db.String(20)))  # will store info can only be: volunteering, donation, adoption, animal foster

    user_location = db.relationship("UserLocation", back_populates="user_preferences")
    user_animal_preferences = db.relationship("UserAnimalPreferences", back_populates="user_preferences")
    user_animal_appearance_preferences = db.relationship("UserAnimalAppearancePreferences", back_populates="user_preferences")
    user_animal_behavior_preferences = db.relationship("UserAnimalBehaviorPreferences", back_populates="user_preferences")


class UserAnimalPreferences(db.Model):
    """Table to capture user preferences on a single type of animal: Must be one of 'dog', 'cat', 'rabbit', 'small-furry', 'horse', 'bird', 'scales-fins-other', or 'barnyard'. 
    """

    __tablename__ = "user_animal_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    user_preferences_id = db.Column(db.Integer, db.ForeignKey("user_preferences.id"))
    species_preference = db.Column(db.ARRAY(db.String))  # Must be one of ‘dog’, ‘cat’, ‘rabbit’, ‘small-furry’, ‘horse’, ‘bird’, ‘scales-fins-other’, or ‘barnyard’.

    user_preferences = db.relationship("UserPreferences", back_populates="user_animal_preferences")
    user_animal_appearance_preferences = db.relationship("UserAnimalAppearancePreferences", back_populates="user_animal_preferences")
    user_animal_behavior_preferences = db.relationship("UserAnimalBehaviorPreferences", back_populates="user_animal_preferences")


class UserAnimalAppearancePreferences(db.Model):

    """Table to capture specific user preferences on animal appearance"""

    __tablename__ = "user_animal_appearance_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    user_preferences_id = db.Column(db.Integer, db.ForeignKey("user_preferences.id"))
    user_animal_preferences_id = db.Column(db.Integer, db.ForeignKey("user_animal_preferences.id"))

    user_preferences = db.relationship("UserPreferences", back_populates="user_animal_appearance_preferences")
    user_animal_preferences = db.relationship("UserAnimalPreferences", back_populates="user_animal_appearance_preferences")


class UserAnimalBehaviorPreferences(db.Model):
    """Table to capture specific user preferences on animal behavior history"""

    __tablename__ = "user_animal_behavior_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    user_preferences_id = db.Column(db.Integer, db.ForeignKey("user_preferences.id"))
    user_animal_preferences_id = db.Column(db.Integer, db.ForeignKey("user_animal_preferences.id"))

    user_preferences = db.relationship("UserPreferences", back_populates="user_animal_behavior_preferences")
    user_animal_preferences = db.relationship("UserAnimalPreferences", back_populates="user_animal_behavior_preferences")


class UserLocation(db.Model):
    "Table to store user location information"

    __tablename__ = "user_location"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    user_preferences_id = db.Column(
        db.Integer, db.ForeignKey("user_preferences.id")
    )
    address = db.Column(db.String)
    state_province = db.Column(db.String, nullable=False)
    postal_code = db.Column(db.String, nullable=False)
    city = db.Column(db.String, nullable=False)
    country = db.Column(db.String, nullable=False)

    user_preferences = db.relationship("UserPreferences", back_populates="user_location")


class UserLocation(db.Model):
    """Table to store user location information"""

    __tablename__ = "user_location"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    user_preferences_id = db.Column(db.Integer, db.ForeignKey("user_preferences.id"))
    address = db.Column(db.String)
    state_province = db.Column(db.String, nullable=False)
    postal_code = db.Column(db.String, nullable=False)
    city = db.Column(db.String, nullable=False)
    country = db.Column(db.String, nullable=False)


class UserTravelPreferences(db.Model):
    """Table to store user and travel preferences"""

    __tablename__ = "user_travel_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    user_preferences_id = db.Column(db.Integer, db.ForeignKey("user_preferences.id"))

    distance_to_location_preference = db.Column(db.Integer)
    willing_to_travel = db.Column(db.Boolean) # general question, if false -> all others are defaulted to false
    willing_to_fly_by_airplane = db.Column(db.Boolean) # eg. for flight buddy opportunities
    willing_to_drive = db.Column(db.Boolean)
    willing_to_carpool = db.Column(db.Boolean)
    willing_to_transport = db.Column(db.Boolean) # transport rescue animals, supplies, be the carpool driver
    willing_to_take_transit = db.Column(db.Boolean)


class UserResources(db.Model):
    """Table to store user resources and capacity to volunteer or care for an animal"""

    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=True)
    user_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=True)
    possesses_car = db.Column(db.Boolean)
    possesses_valid_drivers_license = db.Column(db.Boolean)


class UserResidence(db.Model):
    """Table to store user residence and living situation where the rescue animals could be housed as well"""

    __tablename__ = "user_residence"

    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=True)
    user_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=True)

    #residence location
    is_urban = db.Column(db.Boolean)
    is_rural = db.Column(db.Boolean)

    #resident type
    dwelling_type = db.Column(db.String, nullable=True)
    dwelling_size = db.Column(db.string)
    potential_hazards_description = db.Column(db.string)
    has_yard = db.Column(db.Boolean)
    has_pool = db.Column(db.Boolean)
    has_fence_surrounding_dwelling = db.Column(db.Boolean)
    has_doggie_door = db.Column(db.Boolean)


class UserCurrentPets(db.Model):
    """Table to capture user information regarding the pets living in their residence"""

    __tablename__ = 'user_current_pets'

    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=True)
    user_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=True)

    user_has_pets = db.Column(db.Boolean)
    pet_quantity = db.Column(db.Integer)
    pet_type = db.Column(db.ARRAY(db.String))
    pets_age = db.Column(db.Array(db.String)) #Accepted values: ‘baby’,’young’, ‘adult’, ‘senior’.
    user_pets_has_medical_conditions = db.Column(db.Boolean)

    user_pets_friendly_to_new_dogs = db.Column(db.Boolean)
    user_pets_friendly_to_new_cats = db.Column(db.Boolean)
    user_pets_friendly_to_new_birds = db.Column(db.Boolean)
    user_pets_friendly_to_new_bunnies = db.Column(db.Boolean)
    user_pets_friendly_to_new_misc_animal_types = db.Column(db.Boolean)


def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)
