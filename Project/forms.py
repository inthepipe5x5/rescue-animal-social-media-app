from flask_wtf import FlaskForm  # type: ignore
from wtforms import (  # type: ignore # type: ignore
    StringField,
    PasswordField,
    TextAreaField,
    SelectMultipleField,
    BooleanField,
    SelectField,
    HiddenField,
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


def uppercase_2_chars(form, field):
    """
    Helper form filter function to always output 2 upper case str characters
    Intended to be used for state input fields
    """
    if field.data:
        field.data = field.data.upper()[:2]


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

    state = StringField(
        "State/Province - eg. 'ON'",
        validators=[Length(min=2, max=2), DataRequired(), ValidState()],
        default="ON",
        # filters=uppercase_2_chars #always ensure the output data is 2 upper case str
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
    """Form for adding users.
    Extends:
        - StateCountryForm => For state, country inputs
        - UserExperienceForm => for animal_type & rescue_action_type inputs


    """

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
    """Form to edit Users

    Args:
        ModelForm (FlaskWTForms): _description_
    """

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

    state = StringField(
        "State/Province - eg. 'NY'",
        validators=[Length(min=2, max=2), ValidState()],
        # filters=[uppercase_2_chars]
    )
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


class HiddenForm(FlaskForm):
    """Hidden form to submit CSRF token and any additional data"""

    csrf_token = HiddenField()

class HiddenLocationForm(UserLocationForm):
    """Hidden form to submit CSRF token and location data to be used in API data queries"""

    csrf_token = HiddenField()

    def __init__(self, *args, **kwargs):
        super(HiddenLocationForm, self).__init__(*args, **kwargs)
            
class SpecificAnimalPreferencesForm(FlaskForm):
    """To capture user preferences for specific animal species. To be used as optional filters on animals by behavior and appearance."""

    # Medical Preferences
    declawed = BooleanField("Declawed", default=False)
    shots_current = BooleanField("Immunizations are up to date", default=False)
    special_needs = BooleanField("Special Needs", default=False)
    spayed_neutered = BooleanField("Spayed/Neutered", default=False)
    #Environmental/Interaction Preferences 
    house_trained = BooleanField("House Trained", default=False)
    child_friendly = BooleanField("Friendly to children?", default=False)
    dogs_friendly = BooleanField("Friendly to dogs", default=False)
    cats_friendly = BooleanField("Friendly to cats", default=False)

    breeds = SelectMultipleField(
        "Select Desired Breed(s)",
        choices=[("any", "Any")],
        default=["any"],
        validate_choice=False,
    )
    colors = SelectMultipleField(
        "Select Desired Coat Color(s)",
        choices=[("any", "Any")],
        default=["any"],
        validate_choice=False,
    )
    coat = SelectMultipleField(
        "Select Desired Coat Type(s)",
        choices=[("any", "Any")],
        default=["any"],
        validate_choice=False,
    )

    age = SelectMultipleField(
        "Animal Age Preference",
        choices=[
            ("any", "Any"),
            ("baby", "Baby"),
            ("young", "Young"),
            ("adult", "Adult"),
            ("senior", "Senior"),
            ("unknown", "Unknown"),
        ],
        default=["any"],
    )

    personality_choices = [
        ("any", "Any"),
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

    personality_tags = SelectMultipleField(
        "Animal Personality Tags Preferences",
        choices=personality_choices,
        default=["any"],
    )

    size = SelectMultipleField(
        "Animal Physical Attributes Preferences",
        choices=[
            ("any", "Any"),
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
            ("xlarge", "Extra Large"),
            ("unknown", "Unknown"),
        ],
        default=["any"],
    )

    gender = SelectMultipleField(
        "Gender Preference",
        choices=[
            ("any", "Any"),
            ("male", "Male"),
            ("female", "Female"),
            ("unknown", "Unknown"),
        ],
        default=["any"],
    )
    
    def __init__(self, animal_type, *args, **kwargs):
        super(SpecificAnimalPreferencesForm, self).__init__(*args, **kwargs)
        self.animal_type = animal_type
        api = Petfinder(
            key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET")
        )

        # Fetch dynamic choices
        breed_choices = api.breeds(animal_type)["breeds"][animal_type]
        animals = api.animal_types(animal_type)
        coat_choices = animals["type"]["coats"] or []
        coat_color_choices = animals["type"]["colors"] or []

        # Fetch dynamic choices
        breed_choices = api.breeds(animal_type)["breeds"][animal_type]
        animals = api.animal_types(animal_type)
        coat_choices = animals["type"]["coats"] 
        coat_color_choices = animals["type"]["colors"]

        # Set dynamic choices
        if breed_choices and len(breed_choices) > 0:
            for name in breed_choices:
                self.breeds.choices.append((name, name.capitalize()))

        if coat_choices and len(coat_choices) > 0:
            for name in coat_choices:
                self.coat.choices.append((name, name.capitalize()))

        if coat_color_choices and len(coat_color_choices) > 0:
            for name in coat_color_choices:
                self.colors.choices.append((name, name.capitalize()))


        # # # # Process data from obj after setting choices to populate defaults
        # if "obj" in kwargs and "formdata" not in kwargs:
        #     obj = kwargs["obj"]
        #     self.process(obj=obj)
    
