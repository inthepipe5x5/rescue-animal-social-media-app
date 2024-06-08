"""SQLAlchemy models for app."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY

bcrypt = Bcrypt()
db = SQLAlchemy()


# class Follows(db.Model):
#     """Connection of a follower <-> followed_followed_org."""

#     __tablename__ = "follows"

#     rescue_org_being_followed_id = db.Column(
#         db.Integer,
#         db.ForeignKey("rescueOrg.id", ondelete="cascade"),
#         primary_key=True,
#     )

#     user_following_id = db.Column(
#         db.Integer,
#         db.ForeignKey("users.id", ondelete="cascade"),
#         primary_key=True,
#     )


# class RescueOrganization(db.Model):
#     """Rescue Organization db.Model
#     """

#     __tablename__ = "rescueOrg"

#     id = db.Column(
#         db.Integer,
#         primary_key=True,
#     )

#     name = db.Column(
#         db.Text,
#         nullable=False,
#         unique=True,
#     )


class MatchedRescueOrganization(db.Model):
    """Matched Rescue Organization db.Model captures information about a Rescue Organization and the relationship to a specific user"""

    __tablename__ = "matched_rescue_org"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    matched_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    matched_org_id = db.Column(db.Integer, db.ForeignKey("rescueOrg.id"))
    matched_pct = db.Column(db.Integer, nullable=False, default=0)
    matched_datetime = db.Column(db.DateTime, nullable=False, default=datetime.now())
    followed_by_user_bool = db.Column(db.Boolean, default=False)

    user = db.relationship(
        "User", foreign_keys=[matched_user_id], back_populates="matched_rescue_orgs"
    )


class UserLocation(db.Model):
    """Table to store user location information"""

    __tablename__ = "user_location"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # user_preferences_id = db.Column(
    #     db.Integer, db.ForeignKey("user_preferences.id"), nullable=False
    # )
    country = db.Column(db.String(2), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    # postal_code = db.Column(db.String(7), nullable=False)
    city = db.Column(db.String(100))

    user = db.relationship(
        "User",
        back_populates="location",
        foreign_keys=[user_id],
        remote_side="UserLocation.user_id",
    )

    # user_preferences = db.relationship(
    #     "UserPreferences",
    #     back_populates="user_location",
    #     foreign_keys=[user_preferences_id],
    # )


class User(db.Model):
    """User in the system."""

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    email = db.Column(
        db.Text,
        # nullable=False,
        unique=True,
    )

    username = db.Column(
        db.Text,
        # nullable=False,
        unique=True,
    )

    image_url = db.Column(
        db.Text,
        default="../static/images/profile-images/default-hero-sasha-sashina-YCsh4ltV9Ec-unsplash.jpg",
    )

    header_image_url = db.Column(
        db.Text,
        default="../static/images/profile-images/default-header-image-natalie-kinnear-MUkxOfl8epk-unsplash.jpg",
    )

    bio = db.Column(db.Text)

    password = db.Column(
        db.Text,
        nullable=False,
    )

    # location_id = db.Column(db.Integer, db.ForeignKey("user_location.id"))

    rescue_action_type = db.Column(
        "rescue_action_type", ARRAY(db.String)
    )  # will store info can only be: volunteering, donation, adoption, animal foster

    animal_types = db.Column(
        "animal_types", ARRAY(db.String)
    )  # Must be one of 6 potential values: ‘dog’, ‘cat’, ‘rabbit’, ‘small-furry’, ‘horse’, ‘bird’, ‘scales-fins-other’, or ‘barnyard’. Default='dog'

    registration_date = db.Column(db.DateTime)

    animal_handling_experience = db.Column(
        db.String,
        db.ForeignKey("user_animal_handling_history.id"),
    )
    user_animal_preferences = db.relationship(
        "UserAnimalPreferences", back_populates="user"
    )
    # animal_handling_experiences = db.relationship('UserAnimalHandlingExperience', back_populates='user')
    location = db.relationship(
        "UserLocation",
        back_populates="user",
    )
    matched_rescue_orgs = db.relationship(
        "MatchedRescueOrganization", back_populates="user"
    )
    # followed_orgs = db.relationship("FollowedOrg", back_populates="user")
    # user_reviews = db.relationship("UserReviews", back_populates="user")

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}, {self.bio}, {self.location}>"

    # def is_following(self, specific_org):
    #     """Is this user following any rescue agencies?"""

    #     return specific_org in self.followed_orgs

    @classmethod
    def signup(cls, username, email, password, image_url, rescue_action_type, animal_types, bio=None, **user_data_kwargs):
        """Sign up user.

        Hashes password and adds user to system.
        """

        # Hash the password if provided as a positional argument
        if password:
            hashed_pwd = bcrypt.generate_password_hash(password).decode("utf8")
        else:
            # Check if password is provided in user_data_kwargs
            #use .pop() to prevent additional 'password' keywords being passed
            password = user_data_kwargs.pop("password", None)
            if password:
                hashed_pwd = bcrypt.generate_password_hash(password).decode("utf8")
            else:
                raise ValueError("Password is required for signup.")

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
            image_url=image_url,
            bio=bio,
            animal_types=animal_types,
            rescue_action_type=rescue_action_type,
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

        if user and bcrypt.check_password_hash(user.password, password):
            return user

        return False


# class UserPreferences(db.Model):
#     """Relational table that stores id of the other preferences tables associated with one User"""

#     __tablename__ = "user_preferences"

#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
# user_location_id = db.Column(db.Integer, db.ForeignKey("user_location.id"))

# # unique table data columns
# species_global = db.Column(
#     ARRAY(db.String), default=['dog', 'cat']
# )  # Must be one of ‘dog’, ‘cat’, ‘rabbit’, ‘small-furry’, ‘horse’, ‘bird’, ‘scales-fins-other’, or ‘barnyard’.
# rescue_action_type_global_preference = db.Column(
#     ARRAY(db.String(20))
# )  # will store info can only be: volunteering, donation, adoption, animal foster

# relationships
# user = db.relationship('User', back_populates='preferences')
# user_location = db.relationship("UserLocation", back_populates="user_preferences")
# user_animal_preferences = db.relationship(
#     "UserAnimalPreferences", back_populates="user_preferences"
# )
# user_animal_appearance_preferences = db.relationship(
#     "UserAnimalAppearancePreferences", back_populates="user_preferences"
# )
# user_animal_behavior_preferences = db.relationship(
#     "UserAnimalBehaviorPreferences", back_populates="user_preferences"
# )


class UserAnimalPreferences(db.Model):
    """Table to capture user preferences on a single type of animal: Must be one of 'dog', 'cat', 'rabbit', 'small-furry', 'horse', 'bird', 'scales-fins-other', or 'barnyard'."""

    # table meta information columns
    __tablename__ = "user_animal_preferences"

    id = db.Column(db.Integer, primary_key=True)
    # user_preferences_id = db.Column(db.Integer, db.ForeignKey("user_preferences.id"))

    # table unique data columns
    species = db.Column(
        db.String(20), default="dog"
    )  # captures the specific type of animal species for this preference

    user_preference_name = db.Column(db.String(100), nullable=False)
    user_preference_data = db.Column(db.String(100), nullable=False)

    # user_animal_appearance_preferences_id = db.Column(db.Integer, db.ForeignKey('user_animal_appearance_preferences.id'))
    # user_animal_behavior_preferences_id = db.Column(db.Integer, db.ForeignKey('user_animal_behavior_preferences.id'))

    # db.relationships
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # user_preferences = db.relationship(
    #     "UserPreferences", back_populates="user_animal_preferences"
    # )
    # user_animal_appearance_preferences = db.relationship(
    #     "UserAnimalAppearancePreferences", back_populates="user_animal_preferences", foreign_keys=[user_animal_appearance_preferences_id], remote_side=[id]
    # )
    # user_animal_behavior_preferences = db.relationship(
    #     "UserAnimalBehaviorPreferences", back_populates="user_animal_preferences", foreign_keys=[user_animal_behavior_preferences_id], remote_side=[id]
    # )
    user = db.relationship(
        "User",
        back_populates="user_animal_preferences",
        foreign_keys=[user_id],
        remote_side="User.id",
    )


# class UserAnimalBehaviorPreferences(db.Model):
#     """Table to capture specific user preferences on animal behavior history"""

#     __tablename__ = "user_animal_behavior_preferences"

#     id = db.Column(db.Integer, primary_key=True)
#     # user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
#     user_preferences_id = db.Column(db.Integer, db.ForeignKey("user_preferences.id"))
#     user_animal_preferences_id = db.Column(
#         db.Integer, db.ForeignKey("user_animal_preferences.id")
#     )
#     # user_animal_preferences_species = db.Column(
#     #     db.Integer, db.ForeignKey("user_animal_preferences.species")
#     # )

#     # attributes preferences
#     house_trained = db.Column(db.Boolean)
#     declawed = db.Column(db.Boolean)
#     shots_current = db.Column(db.Boolean)
#     special_needs = db.Column(db.Boolean)
#     spayed_neutered = db.Column(db.Boolean)

#     # environmental preferences
#     child_friendly = db.Column(db.Boolean)
#     dogs_friendly = db.Column(db.Boolean)
#     cats_friendly = db.Column(db.Boolean)

#     # db relationships
#     # user=db.relationship("User", back_populates="user_animal_behavior_preferences", foreign_keys=[user_id])

#     user_preferences = db.relationship(
#         "UserPreferences", back_populates="user_animal_behavior_preferences", foreign_keys=[user_preferences_id]
#     )
#     user_animal_preferences = db.relationship(
#         "UserAnimalPreferences", back_populates="user_animal_behavior_preferences", foreign_keys=[user_animal_preferences_id]
#     )


# class UserAnimalAppearancePreferences(db.Model):
#     """Table to capture specific user preferences on animal appearance"""

#     __tablename__ = "user_animal_appearance_preferences"

#     id = db.Column(db.Integer, primary_key=True)
#     # user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
#     user_preferences_id = db.Column(db.Integer, db.ForeignKey("user_preferences.id"))
#     user_animal_preferences_id = db.Column(
#         db.Integer, db.ForeignKey("user_animal_preferences.id")
#     )
#     user_animal_preferences_species = db.Column(
#         db.Integer, db.ForeignKey("user_animal_preferences.species")
#     )
#     userAnimalAppearanceCategory = db.Column(
#         db.String
#     )  # a column that accepts "gender", "coat", "personality", etc. any of the other appearance types
#     userAnimalAppearanceCategoryValue = db.Column(
#         db.String
#     )  # accepts a value corresponding to userAnimalAppearanceCategory saved

#     # so when querying -> search by category & categoryValue that matches the API search params

#     breeds_preference = db.Column(ARRAY(db.String))
#     animal_coat_preference = db.Column(
#         ARRAY(db.String)
#     )  # eg. ["Hairless","Short","Medium","Long","Wire","Curly"]
#     animal_coat_color_preference = db.Column(
#         ARRAY(db.String)
#     )  # eg. ["Hairless","Short","Medium","Long","Wire","Curly"]
#     animal_age_preference = db.Column(
#         ARRAY(db.String)
#     )  # will store info like "infant (0-6 months)", "young (6 months to 2 years)", "adult ("2 years - 5 years")", "senior (5+ years)"
#     animal_personality_tags_preferences = db.Column(
#         ARRAY(db.String)
#     )  # will store user choices regarding animal personality
#     animal_physical_attributes_preferences = db.Column(
#         ARRAY(db.String)
#     )  # will store user choices regarding animal size eg. x-small, small, medium, large, x-large
#     gender_preference = db.Column(
#         ARRAY(db.String)
#     )  # eg. "["male", "female"]" -> user wants both

#     # db relationships
#     # user=db.relationship("User", back_populates="user_animal_appearance_preferences", foreign_keys=[user_id])

#     user_preferences = db.relationship(
#         "UserPreferences", back_populates="user_animal_appearance_preferences"
#     )
#     user_animal_preferences = db.relationship(
#         "UserAnimalPreferences", back_populates="user_animal_appearance_preferences"
# )


# User Application Data Tables


class UserTravelPreferences(db.Model):
    """Table to store user and travel preferences"""

    __tablename__ = "user_travel_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    user_preferences_id = db.Column(db.Integer, db.ForeignKey("user_preferences.id"))

    distance_filter_preference = db.Column(db.Integer)

    willing_to_fly_by_airplane = db.Column(
        db.Boolean
    )  # eg. for flight buddy opportunities
    willing_to_drive = db.Column(db.Boolean)
    willing_to_carpool = db.Column(db.Boolean)
    willing_to_volunteer_transport = db.Column(
        db.Boolean
    )  # transport rescue animals, supplies, be the carpool driver


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

    # residence location
    is_urban = db.Column(db.Boolean)
    is_rural = db.Column(db.Boolean)

    # resident type
    dwelling_type = db.Column(db.String, nullable=True)
    dwelling_size = db.Column(db.String)
    potential_hazards_description = db.Column(db.String)
    has_yard = db.Column(db.Boolean)
    has_pool = db.Column(db.Boolean)
    has_fence_surrounding_dwelling = db.Column(db.Boolean)
    has_doggie_door = db.Column(db.Boolean)


class UserCurrentPets(db.Model):
    """Table to capture user information regarding the pets living in their residence"""

    __tablename__ = "user_current_pets"

    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=True)
    user_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=True)

    user_has_pets = db.Column(db.Boolean)
    pet_quantity = db.Column(db.Integer)
    pet_type = db.Column(ARRAY(db.String))
    pets_age = db.Column(
        ARRAY(db.String)
    )  # Accepted values: ‘baby’,’young’, ‘adult’, ‘senior’.
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
