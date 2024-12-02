"""User SQLAlchemy models for app."""

from datetime import datetime
import pycountry
from flask_bcrypt import Bcrypt
import pytz
from sqlalchemy import func, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, insert
from sqlalchemy.sql import func
from flask_login import UserMixin
from sqlalchemy.exc import IntegrityError

from Project.core.extensions import db, bcrypt


class UserFavorites(db.Model):
    """Table to store user favorites"""

    __tablename__ = "user_favorites"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="cascade"),
        nullable=False,
        primary_key=True,
    )
    favorite_id = db.Column(
        db.Text,  # API results contain strings
        nullable=False,
        primary_key=True,
    )

    accessed_counter = db.Column(db.Integer, default=0)
    is_animal = db.Column("is_animal", db.Boolean, default=True)

    @classmethod
    def get_favorites(cls, user_id):
        """
        Read function -> Get all favorites of a given user_id
        """
        if not user_id:
            raise ValueError(
                f"No user_id passed into UserFavorites.get_favorites(), got {user_id} instead"
            )
        # Query the database for favorites tied to the user_id and retrieve favorite IDs.
        favorites = (
            cls.query.filter_by(user_id=user_id).with_entities(cls.favorite_id).all()
        )

        if not favorites:
            return []  # Return an empty list instead of raising an exception
        # turn favorites into a set to remove duplicates and then return a list
        return list({fav.favorite_id for fav in favorites})

    @classmethod
    def get_animal_favorites(cls, user_id):
        """
        Read function -> Get all favorites of a given user_id
        """
        if not user_id:
            raise ValueError(
                f"No user_id passed into UserFavorites.get_favorites(), got id:'{user_id}' instead"
            )
        # Query the database for animal favorites where is_animal is True.
        favorites = (
            db.session.query(UserFavorites)
            .filter(UserFavorites.user_id == user_id, UserFavorites.is_animal == True)
            .all()
        )
        if not favorites:
            return []  # Return an empty list instead of raising an exception
        # turn favorites into a set to remove duplicates and then return a list
        return list({fav.favorite_id for fav in favorites})

    @classmethod
    def get_org_favorites(cls, user_id):
        """
        Read function -> Get all favorites of a given user_id
        """
        if not user_id:
            raise ValueError(
                f"No user_id passed into UserFavorites.get_favorites(), got id:'{user_id}' instead"
            )
        # Query the database for animal favorites where is_animal is True.
        favorites = (
            db.session.query(UserFavorites)
            .filter(UserFavorites.user_id == user_id, UserFavorites.is_animal == False)
            .all()
        )
        if not favorites:
            return []  # Return an empty list instead of raising an exception
        # turn favorites into a set to remove duplicates and then return a list
        return list({fav.favorite_id for fav in favorites})

    @classmethod
    def add_favorite(cls, user_id, favorite_id, is_animal=True):
        """
        Create function -> Add a new favorite for a given user_id
        """
        favorite = cls(user_id=user_id, favorite_id=favorite_id, is_animal=is_animal)
        try:
            db.session.add(favorite)
            db.session.commit()
            print(f"Added favorite {favorite_id} to user {user_id}")
        except IntegrityError as e:
            db.session.rollback()
            print(f"Favorite already exists in db: {e}")

    @classmethod
    def toggle_favorite(cls, user_id, favorite_id):
        """
        Update function -> Toggle a favorite for a given user_id
        """
        favorite = cls.query.filter_by(user_id=user_id, favorite_id=favorite_id).first()
        if favorite:
            db.session.delete(favorite)
            print(f"Removed favorite {favorite_id} for user {user_id}")
        else:
            favorite = cls(user_id=user_id, favorite_id=favorite_id)
            db.session.add(favorite)
            print(f"Added favorite {favorite_id} for user {user_id}")
        db.session.commit()

    def unfavorite(self):
        """
        Delete function -> Remove this favorite
        """
        db.session.delete(self)
        db.session.commit()
        print(f"Removed favorite {self.favorite_id} for user {self.user_id}")
        return self.favorite_id

    @classmethod
    def remove_favorite(cls, user_id, favorite_id):
        """
        Delete function -> Remove a specific favorite for a given user_id
        """
        favorite = cls.query.filter_by(user_id=user_id, favorite_id=favorite_id).first()
        if favorite:
            db.session.delete(favorite)
            db.session.commit()
            print(f"Removed favorite {favorite_id} for user {user_id}")
        else:
            print(f"Favorite {favorite_id} not found for user {user_id}")


class UserLocation(db.Model):
    """Table to store user location information"""

    __tablename__ = "user_location"
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    # User
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)

    # Data Columns
    country = db.Column(
        db.String(2), nullable=False, default="CA"
    )  # 2 letter STR abbreviation
    state = db.Column(
        db.String(2), nullable=False, default="ON"
    )  # 2 letter STR abbreviation
    postal_code = db.Column(db.String(7))
    geolocation = db.Column(db.String(100))
    city = db.Column(db.String(150))

    user = db.relationship(
        "User",
        back_populates="location",
        # foreign_keys=[user_id],
        # remote_side="UserLocation.user_id",
    )

    def city_state_country_str(self) -> str:
        """
        Instance method that grabs the city, state and country to return a string "location"
        Returns:
            str: Returns a string describing the "location" parameter required for PetFinderAPI calls
        """
        city = self.city
        state = self.state
        country = self.country

        try:
            if country:
                # parse country string into 2 letter abbreviations
                country = (
                    country
                    if (len(country) == 2)
                    else pycountry.countries.search_fuzzy(country)[0].alpha_2
                )
                if city and state:
                    # parse state string into 2 letter abbreviations
                    state = (
                        state
                        if (len(state) == 2)
                        else pycountry.subdivisions.search_fuzzy(state)[0].code
                    )
                    # return f"{city},{state},{country}" #REMOVE LATER - it's producing "Toronto,ON,CA"
                    return f"{state}, {country}"
                elif state:
                    return f"{state},{country}"
                else:
                    return country
            elif city and state:
                # parse state string into 2 letter abbreviations
                state = (
                    state
                    if (len(state) == 2)
                    else pycountry.subdivisions.search_fuzzy(state)[0].code
                )
                return f"{city},{state}"
            elif state:
                return state
            else:
                raise ValueError("Insufficient location information provided")
        except Exception as e:
            # Log the error
            print(f"Error in city_state_country_str: {str(e)}")
            raise ValueError("Unable to process location information")

    def get_location_info(self):
        """
        The `get_location_info` function returns location information based on available geolocation, postal
        code, city, state, and country data.
        :return: The `get_location_info` method returns information about the location based on the
        available attributes in the object. It first checks if the `geolocation` attribute is available and
        returns it if it exists. If not, it checks for `postal_code`, `city` and `state`, `state` and
        `country`, `country` in that order, and returns the appropriate location information based on the
        """

        if self.geolocation:
            return self.geolocation
        elif self.postal_code:
            return self.postal_code
        elif self.city and self.state:
            return f"{self.city}, {self.state}"
        elif self.state and self.country:
            return f"{self.state}, {self.country}"
        elif self.country:
            return self.country
        else:
            return "Unknown Location"

    def serialize(self):
        """
        The function `serialize` returns a dictionary containing location information attributes of an
        object or None.
        :return: The code snippet is defining a `serialize` method for a class. The method returns a
        dictionary containing the following keys and values:
        """
        return (
            {
                "CURR_LOCATION": self.get_location_info(),
                "city": self.city,
                "state": self.state,
                "country": self.country,
                "geolocation": self.geolocation,
            }
            or None,
        )


class User(db.Model, UserMixin):
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
    )  # Must be one of 8 potential values: "dog", "cat", "rabbit", "small-furry", "horse", "bird", "scales-fins-other", or "barnyard". Default='dog'

    registration_date = db.Column(db.DateTime, server_default=func.now())
    # to store IDs of animals followed by

    favorites = db.relationship("UserFavorite", backref="user", lazy="dynamic")

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

    travel_preference = db.relationship(
        "UserTravelPreferences",
        back_populates="user",
    )

    favorites = db.relationship("UserFavorites", backref="user", lazy="dynamic")

    @property
    def get_all_favorites(self):
        """Get all favorites for this user"""
        favorites = (
            UserFavorites.query.filter_by(user_id=self.id)
            .with_entities(UserFavorites.favorite_id)
            .all()
        )
        return list({fav.favorite_id for fav in favorites})

    def get_favorite(self, favorite_id):
        """Get a specific favorite for this user and increment its counter"""
        favorite = UserFavorites.query.filter_by(
            user_id=self.id, favorite_id=favorite_id
        ).first()
        if favorite:
            favorite.accessed_counter += 1
            db.session.commit()
            print(
                f"Retrieved and updated counter for favorite {favorite_id} of user {self.id}"
            )
            return favorite
        else:
            print(f"Favorite {favorite_id} not found for user {self.id}")
            return None

    def add_favorite(self, favorite_id, is_animal=True):
        """Add a new favorite for this user"""
        favorite = UserFavorites(
            user_id=self.id, favorite_id=favorite_id, is_animal=is_animal
        )
        try:
            db.session.add(favorite)
            db.session.commit()
            print(f"Added favorite {favorite_id} for user {self.id}")
        except IntegrityError:
            db.session.rollback()
            print(f"Favorite {favorite_id} already exists for user {self.id}")

    def remove_favorite(self, favorite_id):
        """Remove a specific favorite for this user"""
        favorite = UserFavorites.query.filter_by(
            user_id=self.id, favorite_id=favorite_id
        ).first()
        if favorite:
            db.session.delete(favorite)
            db.session.commit()
            print(f"Removed favorite {favorite_id} for user {self.id}")
        else:
            print(f"Favorite {favorite_id} not found for user {self.id}")

    def toggle_favorite(self, favorite_id, is_animal):
        """Toggle a favorite for this user"""
        favorite = (
            db.session.query(UserFavorites)
            .filter(user_id=self.id)
            .and_(favorite_id=favorite_id)
            .and_(is_animal=is_animal)
            .first()
        )
        if favorite:
            db.session.delete(favorite)
            print(f"Removed favorite {favorite_id} for user {self.id}")
        else:
            favorite = UserFavorites(user_id=self.id, favorite_id=favorite_id)
            db.session.add(favorite)
            print(f"Added favorite {favorite_id} for user {self.id}")
        db.session.commit()

    def update_favorite_counter(self, favorite_id):
        """Increment the accessed_counter for a specific favorite"""
        favorite = UserFavorites.query.filter_by(
            user_id=self.id, favorite_id=favorite_id
        ).first()
        if favorite:
            favorite.accessed_counter += 1
            db.session.commit()
            print(f"Updated counter for favorite {favorite_id} of user {self.id}")
        else:
            print(f"Favorite {favorite_id} not found for user {self.id}")

    @property
    def animal_prefs(self):
        """Returns user animal preferences in a serialized python dict if truthy user animal preferences else seeds

        Returns:
            animal prefs (dict): serialized user animal preferences
        """
        # Get user preferences or query db
        prefs = self.user_animal_preferences or (
            db.session.query(UserAnimalPreferences)
            .filter(UserAnimalPreferences.user_id == self.id)
            .all()
        )

        if prefs:
            # Group preferences by species, creating a dictionary where each species key has a list of preferences
            dict_of_preferences_by_species = {}
            if prefs:
                for pref in prefs:
                    dict_of_preferences_by_species.setdefault(pref.species, []).append(
                        pref
                    )

            # Serialize each preference object in the dictionary
            animal_prefs = {}
            for animal_type, preferences_list in dict_of_preferences_by_species.items():
                animal_prefs[animal_type] = {
                    pref.user_preference_name: pref.user_preference_data
                    for pref in preferences_list
                }

            # return serialized dict
            return animal_prefs
        # handle if no animal preferences
        else:
            # seed preferences
            return UserAnimalPreferences.seed_user_pref(user_id=self.id)

    def serialize(self):
        """Serialize this ORM model class into a python dict

        Returns:
            obj (dict): serialized dict of this user columns
        """

        obj = {
            "id": self.id,
            "animal_types": self.animal_types,
            "rescue_interaction_type": self.rescue_action_type,
            "bio": self.bio,
            "favorites": self.get_all_favorites or [],
            "location": {
                "CURR_LOCATION": self.location.get_location_info(),
                "city": self.location.city,
                "state": self.location.state,
                "country": self.location.country,
                "geolocation": self.location.geolocation,
            }
            or UserLocation().serialize(),
            "distance_pref": UserTravelPreferences._get_distance_filter_param(
                user_id=self.id
            ),
            "animal_pref_dict": self.animal_prefs
            or {ani_type: None for ani_type in self.animal_types},
        }
        return obj

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}, {self.bio}, {self.location}>"

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
            db.session.query(
                UserAnimalPreferences.user_preference_name,
                UserAnimalPreferences.user_preference_data,
            )
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
                "results": {},
            }
        else:
            out = {"user_id": u_id, "species": animal_type}
            for preference in results:
                # add result to out if matches user_id and species
                if preference.user_id == u_id and preference.species == animal_type:
                    # parse JSON value to python values
                    key = (
                        preference.user_preference_name if key != "color" else "colors"
                    )
                    value = preference.user_preference_data
                    out[key] = value
            # handle bad keys
            if "color" in [result.keys() for result in results.values()]:
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
                db.session.query(UserAnimalPreferences)
                .filter(UserAnimalPreferences.user_id == u_id)
                .all()
            )
            print(results)
            # Group preferences by animal_type
            output = {
                type: [
                    result
                    for result in results
                    if result.species.lower() == type.lower()
                ]
                for type in user.animal_types
            }
            return output
        return None  # In case user is not found, though get_or_404 should handle this

    @classmethod
    def seed_user_pref(cls, user_id):
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

            pref_obj_template = {
                "species": animal,
                "user_preference_name": None,
                "user_preference_data": None,
                "user_id": user_id,
            }
            default_bool_prefs = [
                "spayed_neutered",
                "house_trained",
                "declawed",
                "special_needs",
                "shots_current",
                "child_friendly",
                "dogs_friendly",
                "cats_friendly",
            ]
            default_attr_prefs = [
                "breed",
                "coat",
                "color",
                "gender",
                "size",
                "personality",
                "age",
            ]

        pref_list = []

        for animal in all_animal_types:
            for pref in default_bool_prefs:
                pref_obj = pref_obj_template.copy()
                pref_obj["user_preference_name"] = pref
                pref_obj["user_preference_data"] = False

                pref_list.append(pref_obj)

            for pref in default_attr_prefs:
                pref_obj = pref_obj_template.copy()
                pref_obj["user_preference_name"] = pref
                pref_obj["user_preference_data"] = "any"

                pref_list.append(pref_obj)

        # Bulk insert the data into the database
        if pref_list:
            db.session.bulk_insert_mappings(cls, pref_list)
            db.session.commit()
        else:
            db.session.rollback()
        print(f"Seeded animal preferences for User:{user_id} {pref_list}")
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

    distance_filter_preference = db.Column(db.Integer, default=100)

    willing_to_fly_by_airplane = db.Column(
        db.Boolean
    )  # eg. for flight buddy opportunities
    willing_to_drive = db.Column(db.Boolean)
    willing_to_carpool = db.Column(db.Boolean)
    willing_to_volunteer_transport = db.Column(
        db.Boolean
    )  # transport rescue animals, supplies, be the carpool driver

    user = db.relationship("User", back_populates="travel_preference")
    # Add check constraints
    __table_args__ = (
        CheckConstraint(
            "distance_filter_preference >= 0 AND distance_filter_preference <= 500",
            name="check_distance_filter_range",
        ),
    )

    @classmethod
    def _get_distance_filter_param(cls, user_id=None) -> int:
        """
        Utility function that takes in a user id and returns distance_filter_preference (int)
        If no distance_filter_preference found or falsy user_id passed in, default distance_filter_preference of 100 will be returned
        Args:
            user_id (INT, optional): user id to match in search. Defaults to None.

        Returns:
            _type_: _description_
        """
        if not user_id:
            # default
            return 100
        # distance_pref = db.session.query(cls).filter(user_id == user_id).first()
        distance_pref = cls.query.filter_by(user_id=user_id).first()
        # If no distance_filter_preference found or falsy user_id passed in, default distance_filter_preference of 100 will be returned
        return (
            distance_pref.distance_filter_preference
            if distance_pref and distance_pref.distance_filter_preference
            else 100
        )


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
