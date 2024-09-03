"""SQLAlchemy models for app."""

from datetime import datetime
import pycountry
import json
from flask import abort
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, insert

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


class RescueOrganization(db.Model):
    """Rescue Organization db.Model"""

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
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    # user_preferences_id = db.Column(
    #     db.Integer, db.ForeignKey("user_preferences.id"), nullable=False
    # )
    country = db.Column(db.String(2), nullable=False, default="CA")
    state = db.Column(db.String(2), nullable=False, default="ON")
    # postal_code = db.Column(db.String(7), nullable=False)
    city = db.Column(db.String(100))

    user = db.relationship(
        "User",
        back_populates="location",
        # foreign_keys=[user_id],
        # remote_side="UserLocation.user_id",
    )

    def getLocStr(self) -> str:
        """
        Instance method that grabs the city, state and country to return a string "location"
        Returns:
            str: Returns a string describing the "location" parameter required for PetFinderAPI calls

        """
        city = self.city
        state = self.state
        country = self.country

        if country:
            # parse country string into 2 letter abbreviations
            country = (
                country
                if (len(country) == 2)
                else pycountry.countries.search_fuzzy(country)[0].alpha_2
            )
        elif city:  # if city, state, country
            # clean city, state, country strings

            if state:
                # parse state string into 2 letter abbreviations
                state = (
                    state
                    if (len(state) == 2)
                    else pycountry.subdivisions.search_fuzzy(state)[0].alpha_2
                )
                return {
                    "location": "%s,%s" % (city, state),
                    "state": state,
                    "country": country,
                    "city": city,
                }
        else:  # if state, country
            if state:
                return {
                    "location": "%s,%s" % (state, country),
                    "state": state,
                    "country": country,
                }
            else:  # if only country
                return {
                    "location": "%s" % (country),
                    "country": country,
                }


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

    # location_id = db.Column(db.Integer, db.ForeignKey("UserLocation.id"))

    rescue_action_type = db.Column(
        "rescue_action_type",
        ARRAY(db.String),
        server_default=db.text(
            "ARRAY['volunteering', 'donation', 'adoption', 'animal foster']"
        ),
    )  # will store info can only be: volunteering, donation, adoption, animal foster

    animal_types = db.Column(
        "animal_types", ARRAY(db.String), server_default=db.text("ARRAY['dog']")
    )  # Must be one of 6 potential values: "dog", "cat", "rabbit", "small-furry", "horse", "bird", "scales-fins-other", or "barnyard". Default='dog'

    registration_date = db.Column(db.DateTime)

    user_animal_preferences = db.relationship(
        "UserAnimalPreferences",
        back_populates="user",  # , on_delete="CASCADE" #commented out on_delete because it gave a not accepted here error
    )
    location = db.relationship(
        "UserLocation",
        back_populates="user",
        # on_delete="CASCADE",
        uselist=False,  # set to true if you want 1:M ie. one user has many locations; else false => 1 user: 1 location
    )
    matched_rescue_orgs = db.relationship(
        "MatchedRescueOrganization", back_populates="user"
    )

    # followed_orgs = db.relationship("FollowedOrg", back_populates="user")
    # user_reviews = db.relationship("UserReviews", back_populates="user")
    def serialize(self):
        obj = {"username": self.username, "id": self.id, "image_url": self.image_url}
        return obj

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}, {self.bio}, {self.location}>"

    # def is_following(self, specific_org):
    #     """Is this user following any rescue agencies?"""

    #     return specific_org in self.followed_orgs

    @classmethod
    def signup(
        cls,
        username,
        email,
        password,
        image_url,
        rescue_action_type,
        animal_types,
        bio=None,
        **user_data_kwargs,
    ):
        """Sign up user.

        Hashes password and adds user to system.
        """

        # Hash the password if provided as a positional argument
        if password:
            hashed_pwd = bcrypt.generate_password_hash(password).decode("utf8")
        else:
            # Check if password is provided in user_data_kwargs
            # use .pop() to prevent additional 'password' keywords being passed
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


class UserAnimalPreferences(db.Model):
    """Table to capture user preferences on a single type of animal."""

    __tablename__ = "user_animal_preferences"
    id = db.Column(db.Integer, primary_key=True)
    species = db.Column(db.String(20), default="dog", nullable=False)
    user_preference_name = db.Column(db.String(100), nullable=False)
    user_preference_data = db.Column(
        JSONB, nullable=True
    )  # set nullable=True #store as JSON values to handle both strings and lists

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship(
        "User",
        back_populates="user_animal_preferences",
        foreign_keys=[user_id],
        remote_side="User.id",
    )

    # # This will ensure that these columns together uniquely identify a record in the table, and the ON CONFLICT clause can use this constraint to perform the conflict resolution.
    # __table_args__ = tuple(
    UniqueConstraint(
        "user_id", "species", "user_preference_name", name="unique_animal_preference"
    )
    # )

    @classmethod
    def get_user_animal_pref_obj(cls, u_id, animal_type="dog"):
        """
        The function `get_user_animal_preference` retrieves a user's preferences for a specific animal
        species from a database.

        Returns: a python object of animal_preferences
        """
        results = (
            db.session.query(UserAnimalPreferences)
            .filter(
                UserAnimalPreferences.user_id == u_id,
                UserAnimalPreferences.species == animal_type,
            )
            .all()
        )

        if not results or len(results) == 0:
            # handle no results with a 404 error
            return {
                "success_flag": False,
                "statusCode": 404,
                "message": "No results found",
                "results": [],
            }
        else:
            out = {"user_id": u_id, "species": animal_type}
            for preference in results:
                # add result to out if matches user_id and species
                if preference.user_id == u_id and preference.species == animal_type:
                    # parse JSON value to python values
                    key = preference.user_preference_name
                    value = preference.user_preference_data
                    out[key] = value
            # handle bad keys
            if "color" in results:
                results["colors"] = results["color"]
                del results["color"]
            return {
                "success_flag": True,
                "statusCode": 200,
                "message": f"Results found for user: {u_id} for type: {animal_type}",
                "results": out,
            }

    @classmethod
    def get_all_user_animal_preferences(cls, u_id):
        """
        Function to return ALL animal_preferences regardless of species
        """
        user = User.query.get_or_404(u_id)
        if user:
            results = (
                db.session.query(User, UserAnimalPreferences)
                .join(UserAnimalPreferences)
                .filter(User.id == u_id)
                .filter(UserAnimalPreferences.species == func.any(user.animal_types))
                .all()
            )
            return results
        return None  # In case user is not found, though get_or_404 should handle this

    @classmethod
    def seed_user_pref(cls, user_id, form):
        """Seeds animal preferences for the user

        Args:
            user_id (int): ID of the user for whom preferences are being seeded
        """
        all_animal_types = [
            "dog",
            "cat",
            "rabbit",
            "small-furry",
            "horse",
            "bird",
            "scales-fins-other",
            "barnyard",
        ]

        # List to contain the data objects to insert
        pref_list = []

        for animal in all_animal_types:
            pref_form = form(animal)
            # add pref_form to pref_list
            for pref_key, pref_value in pref_form.data.items():
                if pref_key != "csrf_token":
                    # object to be copied and inserted into pref_list

                    # handle if pref_value is [] with no real values
                    if isinstance(pref_value, list) and len(pref_value) == 0:
                        pref_value.append("any")

                    pref_obj = {
                        "species": animal,
                        "user_preference_name": pref_key,
                        "user_preference_data": json.dumps(pref_value),
                        "user_id": user_id,
                    }

                # Append pref_data to pref_list
                pref_list.append(pref_obj)

        # Bulk insert the data into the database
        if pref_list:
            db.session.bulk_insert_mappings(cls, pref_list)
            db.session.commit()
        else:
            db.session.rollback()

        return pref_list

    @classmethod
    def update_user_pref(cls, user_id, species, form_data_obj):
        """Updates animal preferences for the user

        Args:
            user_id (int): ID of the user for whom preferences are being updated
            species: type of animal
            form_data_obj (dict): WTForms.data.items()
        """

        # List to contain the data objects to insert
        pref_list = []
        # grab previous preferences stored
        prev_prefs = (
            db.session.query(UserAnimalPreferences)
            .filter(
                UserAnimalPreferences.user_id == user_id,
                UserAnimalPreferences.species == species,
            )
            .all()
        )
        # loop through Result objects and update with new values
        for pref_obj in prev_prefs:
            if pref_obj.species == species and pref_obj.user_id == user_id:
                data_name = pref_obj.user_preference_name
                if data_name in form_data_obj:
                    # update the result object with the new values from submitted form
                    pref_obj.user_preference_data = form_data_obj[data_name]
                    new_obj = {
                        "id": pref_obj.id,
                        "user_preference_name": data_name,
                        "user_preference_data": form_data_obj[data_name],
                        "species": species,
                    }
                    # Append pref_data to pref_list
                    pref_list.append(new_obj)
        try:
            # Bulk insert the data into the database
            if len(pref_list) > 0:
                updated_prefs = db.session.bulk_update_mappings(cls, pref_list)
                db.session.commit()
                return updated_prefs
            else:
                raise Exception("No preferences passed in to be saved")
        except Exception as e:
            print(e)
            db.session.rollback()
            return


# User Application Data Tables


class UserTravelPreferences(db.Model):
    """Table to store user and travel preferences"""

    __tablename__ = "user_travel_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # user_preferences_id = db.Column(db.Integer, db.ForeignKey("user_preferences.id"))

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
    )  # Accepted values: "baby","young", "adult", "senior".
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
