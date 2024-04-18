from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    SelectMultipleField,
    BooleanField,
    SelectField
)
from wtforms.validators import DataRequired, Email, Length
from wtforms_alchemy import model_form_factory
import pycountry

from models import (
    db,
    User,
    # UserAnimalBehaviorPreferences,
    # UserAnimalAppearancePreferences,
    UserLocation,
    UserTravelPreferences,
)
from PetFinderAPI import pf_api


class MessageForm(FlaskForm):
    """Form for adding/editing messages."""

    text = TextAreaField("text", validators=[DataRequired()])


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[Length(min=6)])


BaseModelForm = model_form_factory(FlaskForm)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(cls):
        return db.session


class UserAddForm(ModelForm):
    """Form for adding users."""

    # Rescue Action Type
    rescue_action_type = SelectMultipleField(
        "Select all the aspects of animal rescue you want to get involved in",
        choices=[
            ("volunteer", "Looking to Volunteer"),
            ("foster", "Animal Fostering"),
            ("adopter", "Looking to Adopt"),
            ("donation", "Donation"),
        ],
        coerce=str,
        default=["volunteer", "foster", "adopter", "donation"],
    )
    class Meta:
        model = User
        exclude = ["rescue_action_type", "registration_date"]
class CountryForm(ModelForm):    
    
    country=SelectField(
        'Country To Search'
        choices=[(alpha_2, name) for alpha_2, name in pycountry.countries.items()], default='CA'
        )

class UserExperiencesForm(FlaskForm):
    """Form for the mandatory onboarding during consumer user registration to fetch & filter API data

    Args:
        FlaskForm (_type_): FlaskForm is a base class provided by Flask-WTF for creating forms in Flask applications.
    """
    # Define a dictionary mapping string values (eg. to be stored in db or used in API calls) to emoji labels
    animal_type_emojis = {
        "dog": "🐶 Dog",
        "cat": "🐱 Cat",
        "rabbit": "🐰 Rabbit",
        "small-furry": "🐹 Small-Furry",
        "horse": "🐴 Horse",
        "bird": "🐦Birds",
        "scales-fins-other": "🦎 Scales, Fins, Other",
        "barnyard": "🐄 Barnyard",
    }


    # Define the SelectMultipleField with the emoji labels
    animal_types = SelectMultipleField(
        "What kind of animal rescue are you interested in? Select the animals you want to search for",
        choices=[
            (str_value, emoji_key)
            for str_value, emoji_key in animal_type_emojis.items()
        ],
        coerce=str,
        default=[["dog", "cat"]],
        validators=[DataRequired()],
    )

    country = CountryForm()

class AnonExperiencesForm(UserExperiencesForm):
    
    # Define the SelectMultipleField with the emoji labels
    animal_types = SelectField(
        "What kind of animal rescue are you interested in? Select the animals you want to search for",
        choices=[
            (str_value, emoji_key)
            for str_value, emoji_key in UserExperiencesForm.animal_type_emojis.items()
        ],
        coerce=str,
        default=["dog"],
        validators=[DataRequired()],
    )

class UserEditForm(ModelForm):

    username = StringField("Username", validators=[DataRequired()])
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[Length(min=6)])
    image_url = TextAreaField("(Optional) Image URL")
        # Rescue Action Type
    rescue_action_type = SelectMultipleField(
        "Select all the aspects of animal rescue you want to get involved in",
        choices=[
            ("volunteer", "Looking to Volunteer"),
            ("foster", "Animal Fostering"),
            ("adopter", "Looking to Adopt"),
            ("donation", "Donation"),
        ],
        coerce=str,
        default=["volunteer", "foster", "adopter", "donation"],
    )
    
    # Define a dictionary mapping string values (eg. to be stored in db or used in API calls) to emoji labels
    animal_type_emojis = {
        "dog": "🐶 Dog",
        "cat": "🐱 Cat",
        "rabbit": "🐰 Rabbit",
        "small-furry": "🐹 Small-Furry",
        "horse": "🐴 Horse",
        "bird": "🐦Birds",
        "scales-fins-other": "🦎 Scales, Fins, Other",
        "barnyard": "🐄 Barnyard",
    }

    # Define the SelectMultipleField with the emoji labels
    animal_types = SelectMultipleField(
        "What kind of animal rescue are you interested in? Select the animals you want to search for",
        choices=[
            (str_value, emoji_key)
            for str_value, emoji_key in animal_type_emojis.items()
        ],
        coerce=str,
        default=["dog", "cat"],
        validators=[DataRequired()],
    )
    
    state = StringField("State/Province - eg. 'NY'", validators=[Length(max=2)])
    bio = TextAreaField("(Optional) Tell us about what makes you interested in animal rescue?")


class UserLocationForm(ModelForm):
    """Form for adding user location information"""

    class Meta:
        model = UserLocation
        exclude = ['country']
    country = CountryForm()

class UserTravelForm(ModelForm):
    """Optional form for adding user travel preferences"""

    class Meta:
        model = UserTravelPreferences


class SpecificAnimalPreferencesForm(FlaskForm):
    """To capture user preferences for specific animal species. To be used as optional filters on animals by behavior and appearance."""

    # Medical Preferences
    class MedicalPreferencesSection:
        declawed = BooleanField("Declawed", default=False)
        shots_current = BooleanField("Immunizations are up to date", default=False)
        special_needs = BooleanField("Special Needs", default=False)
        spayed_neutered = BooleanField("Spayed/Neutered", default=False)

    # Animal Training & Socialization Preferences
    class TrainingSocializationSection:
        house_trained = BooleanField("House Trained", default=False)
        child_friendly = BooleanField("Friendly to children?", default=False)
        dogs_friendly = BooleanField("Friendly to dogs", default=False)
        cats_friendly = BooleanField("Friendly to cats", default=False)

    # Appearance Preferences
    class AppearancePreferencesSection:
        breeds = SelectMultipleField("", choices=[], default=False)

        # Coat Preferences
        color = SelectMultipleField(
            "Animal Coat Preference",
            choices=[],
            default=[],
        )
        coat = SelectMultipleField(
            "Animal Coat Color Preference",
            choices=[
                ("Hairless", "Hairless"),
                ("Short", "Short"),
                ("Medium", "Medium"),
                ("Long", "Long"),
                ("Wire", "Wire"),
                ("Curly", "Curly"),
            ],
            default=["Hairless", "Short", "Medium", "Long", "Wire", "Curly"],
        )

        # Age Preferences
        age = SelectMultipleField(
            "Animal Age Preference",
            choices=[
                ("baby", "baby"),
                ("young", "young"),
                ("adult", "adult"),
                ("senior", "senior"),
            ],
            default=["baby", "young", "adult", "senior"],
        )

    # Personality Preferences
    class PersonalityPreferencesSection:
        animal_personality_tags_preferences = SelectMultipleField(
            "Animal Personality Tags Preferences",
            choices=[
                ("cute", "Cute"),
                ("intelligent", "Intelligent"),
                ("friendly", "Friendly"),
                ("affectionate", "Affectionate"),
                ("energetic", "Energetic"),
                ("calm", "Calm"),
                ("curious", "Curious"),
                ("loyal", "Loyal"),
                ("active", "Active"),
                ("lazy", "Lazy"),
                ("gentle", "Gentle"),
                ("sweet", "Sweet"),
            ],
            default=[],
        )

    # Size Preferences
    class SizePreferencesSection:
        size = SelectMultipleField(
            "Animal Physical Attributes Preferences",
            choices=[
                ("small", "Small"),
                ("medium", "Medium"),
                ("large", "Large"),
                ("xlarge", "Extra Large"),
            ],
            default=["small", "medium", "large", "xlarge"],
        )

    # Gender Preferences
    class GenderPreferencesSection:
        gender = SelectMultipleField(
            "Gender Preference",
            choices=[("male", "Male"), ("female", "Female")],
            default=["male", "female"],
        )
