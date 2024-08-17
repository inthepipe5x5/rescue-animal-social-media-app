from flask_wtf import FlaskForm  # type: ignore
from wtforms import (  # type: ignore # type: ignore
    StringField,
    PasswordField,
    TextAreaField,
    SelectMultipleField,
    BooleanField,
    SelectField,
)
from petpy import Petfinder
import os

from wtforms.validators import DataRequired, Email, Length, ValidationError  # type: ignore
from wtforms_alchemy import model_form_factory  # type: ignore
import pycountry  # type: ignore

from .models import (
    db,
    User,
    # UserAnimalBehaviorPreferences,
    # UserAnimalAppearancePreferences,
    UserLocation,
    UserTravelPreferences,
)

# from package.PetFinderAPI import api


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


class ValidState(object):
    """Custom validator for state WTForm field because creating a SelectField with pycountry.subdivisions as options is too long"""

    def __init__(self, message=None):
        self.message = message or "Invalid state passed in."

    def __call__(self, form, field):
        country_code = form.country.data
        state_code = field.data
        if not country_code or not state_code:
            raise ValidationError(self.message)

        try:
            # Find the country by its alpha-2 code
            country = pycountry.countries.get(alpha_2=country_code)
            if not country:
                raise ValidationError(f"Invalid country code: {country_code}")

            # Find the subdivision (state) by code and ensure it belongs to the correct country
            subdivisions = pycountry.subdivisions.get(
                code=f"{country.alpha_2}-{state_code}"
            )
            if not subdivisions:
                raise ValidationError(
                    f"Invalid state code: {state_code} for country: {country.alpha_2}"
                )

        except LookupError:
            raise ValidationError(self.message)


class StateCountryForm(ModelForm):
    countries_list = list(pycountry.countries)

    country = SelectField(
        "What Country are you located in?",
        choices=[(country.alpha_2, country.name) for country in countries_list],
        default="CA",
        validators=[DataRequired()],  # ensure no empty values
    )

    # state = SelectField(
    #     "What State or Province are you located in?",
    #     choices=[
    #         (state.code, state.name)
    #         for state in list(pycountry.subdivisions)
    #         if state.type in ["province", "state", "territory"]
    #     ],
    #     default="ON",
    #     validators=[DataRequired()],  # ensure no empty values
    # )

    state = StringField(
        "State/Province - eg. 'ON'",
        validators=[Length(max=2), DataRequired(), ValidState()],
    )


class UserExperiencesForm(StateCountryForm):
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
        default=["dog"],
        validators=[DataRequired()],
    )


class UserAddForm(UserExperiencesForm):
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
        validators=[DataRequired()],
    )

    email = StringField("Email", validators=[Email()])

    class Meta:
        model = User
        exclude = ["rescue_action_type", "registration_date", "animal_types"]

    # customize individual animal type preferences


class GlobalPreferencesForm(FlaskForm):
    """Form for users to indicate if they want to customize their preferences

    Args:
        FlaskForm (_type_): Flask subclass of WTForms
    """

    def __init__(self):
        # animal types
        animal_dict = UserExperiencesForm.animal_type_emojis
        for value, label in animal_dict:
            self[value] = BooleanField(label, default=False)

    travel = BooleanField(
        "Would you like to customize your travel preferences?", default=False
    )
    # user info
    residence = BooleanField("Would you like to describe your living situation?")
    resources = BooleanField("Would you like to describe your resources?")
    residence = BooleanField("Would you like to describe your living situation?")
    residence = BooleanField("Would you like to describe your living situation?")


class AnonExperiencesForm(UserExperiencesForm):

    # Define the SelectMultipleField with the emoji labels
    animal_types = SelectField(
        "Select the animals you want to search for",
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
    bio = TextAreaField(
        "(Optional) Tell us about what makes you interested in animal rescue?"
    )


class UserLocationForm(StateCountryForm):
    """
    Form for adding user location information
    """

    class Meta:
        model = UserLocation
        # exclude country & state fields to utilize StateCountryForm instead
        exclude = ["country", "state"]


class UserTravelForm(ModelForm):
    """Optional form for adding user travel preferences"""

    class Meta:
        model = UserTravelPreferences


class SpecificAnimalPreferencesForm(FlaskForm):
    """To capture user preferences for specific animal species. To be used as optional filters on animals by behavior and appearance."""

    def __init__(self, animal_type, *args, **kwargs):
        super(SpecificAnimalPreferencesForm, self).__init__(*args, **kwargs)
        self.animal_type = animal_type
        api = Petfinder(
            key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET")
        )

        breed_choices = api.breeds(animal_type)["breeds"][animal_type]
        animals = api.animal_types(animal_type)

        # print("Breed choices:", breed_choices)
        # print("API form choices:", animals)

        coat_choices = animals["type"]["coats"] or []
        coat_color_choices = animals["type"]["colors"] or []

        # Dynamically populate form choices based on API results
        if breed_choices:
            self.breeds.default = breed_choices
            self.breeds.choices = [(name, name.capitalize()) for name in breed_choices]
            # update the form
            self.process()
        if coat_choices:
            self.coat.default = coat_choices
            self.coat.choices = [(name, name.capitalize()) for name in coat_choices]
            # update the form
            self.process()
        if coat_color_choices:
            self.color.default = coat_color_choices
            self.color.choices = [
                (name, name.capitalize()) for name in coat_color_choices
            ]
            # update the form
            self.process()

    # Medical Preferences
    declawed = BooleanField("Declawed", default=False)
    shots_current = BooleanField("Immunizations are up to date", default=False)
    special_needs = BooleanField("Special Needs", default=False)
    spayed_neutered = BooleanField("Spayed/Neutered", default=False)

    # Animal Training & Socialization Preferences
    house_trained = BooleanField("House Trained", default=False)
    child_friendly = BooleanField("Friendly to children?", default=False)
    dogs_friendly = BooleanField("Friendly to dogs", default=False)
    cats_friendly = BooleanField("Friendly to cats", default=False)

    # Appearance Preferences
    breeds = SelectMultipleField("Breed Preferences", choices=[], validate_choice=False) #set validate_choice=False because choices are dynamically populated which interacts poorly with validate_choices=True
    color = SelectMultipleField("Animal Coat Color Preference", choices=[], validate_choice=False) #set validate_choice=False because choices are dynamically populated which interacts poorly with validate_choices=True
    coat = SelectMultipleField("Animal Coat Preference", choices=[], validate_choice=False) #set validate_choice=False because choices are dynamically populated which interacts poorly with validate_choices=True

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
    personality_choices = [
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
    ]
    # Personality Preferences
    personality_tags = SelectMultipleField(
        "Animal Personality Tags Preferences",
        choices=personality_choices,
        default=[value for value, label in personality_choices],
    )

    # Size Preferences
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
    gender = SelectMultipleField(
        "Gender Preference",
        choices=[("male", "Male"), ("female", "Female")],
        default=["male", "female"],
    )
