from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    SelectMultipleField,
    BooleanField,
)
from wtforms.validators import DataRequired, Email, Length
from wtforms_alchemy import model_form_factory
from models import (
    db,
    User,
    UserAnimalBehaviorPreferences,
    UserAnimalAppearancePreferences,
)
from PetFinderAPI import pf_api


class MessageForm(FlaskForm):
    """Form for adding/editing messages."""

    text = TextAreaField("text", validators=[DataRequired()])


BaseModelForm = model_form_factory(FlaskForm)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(cls):
        return db.session


class UserAddForm(ModelForm):
    """Form for adding users."""

    class Meta:
        model = User

    location = StringField(
        "Please Enter Your Location (Country, state/province, city OR postal code)",
        validators=[DataRequired()],
    )

class UserEditForm(ModelForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[Length(min=6)])
    image_url = TextAreaField("(Optional) Image URL")
    # location = StringField(
    #     "Location (Country, state/province, city OR postal code)",
    #     validators=[DataRequired()],
    # )
    bio = TextAreaField("(Optional) Tell me about yourself!")


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[Length(min=6)])


class MandatoryOnboardingForm(FlaskForm):
    """Form for the mandatory onboarding during consumer user registration to fetch & filter API data

    Args:
        FlaskForm (_type_): FlaskForm is a base class provided by Flask-WTF for creating forms in Flask applications.
    """


    # Define a dictionary mapping string values (eg. to be stored in db or used in API calls) to emoji labels
    animal_type_emojis = {
        "dog": "🐶",
        "cat": "🐱",
        "rabbit": "🐰",
        "small-furry": "🐹",
        "horse": "🐴",
        "bird": "🐦",
        "scales-fins-other": "🐠",
        "barnyard": "🐄",
    }

    # Define the SelectMultipleField with the emoji labels
    animal_types = SelectMultipleField(
        "What kind of animal rescue are you interested in? Select the animals you want to search for",
        choices=[
            (str_key, emoji_value)
            for str_key, emoji_value in animal_type_emojis.items()
        ],
        coerce=str,
    )


# class userSearchOptionsPreferencesForm(ModelForm):
#     """Form to capture user preferences for specific animal traits: behavior, medical history, physical traits
#     If none, user prefers to omit during search process. Intended to be linked to UserPreferences or

#     Args:
#         ModelForm (class): a base class provided by Flask-WTF-SQLAlchemy extension for creating forms that are automatically generated from SQLAlchemy models
#     """

    behavior_medical_bool = BooleanField(
        "Search by animal behavior or medical history?", default=False
    )
    # behavior options

    # breeds
    breeds_preference_bool = BooleanField(
        "Searching for specific breeds?", default=False
    )

    # physical traits
    appearance_bool = BooleanField("Search by physical traits?", default=False)


class SpecificAnimalBehaviorPreferenceForm(ModelForm):
    """To capture user preferences for specific animal species. To be used to as optional filters on animals by behavior

    Args:
        ModelForm (class): a base class provided by Flask-WTF-SQLAlchemy extension for creating forms that are automatically generated from SQLAlchemy models
    """

    # class Meta:
    #     model = UserAnimalBehaviorPreferences

    # medical/behavior/attributes preferences
    house_trained = BooleanField("House Trained", default=False)
    declawed = BooleanField("Declawed", default=False)
    shots_current = BooleanField("Immunizations are up to date", default=False)
    special_needs = BooleanField("Special Needs", default=False)
    spayed_neutered = BooleanField("Spayed/Neutered", default=False)

    # animal reactivity preferences
    child_friendly = BooleanField("Friendly to children?", default=False)
    dogs_friendly = BooleanField("Friendly to dogs", default=False)
    cats_friendly = BooleanField("Friendly to cats", default=False)


class SpecificAnimalAppearancePreferenceForm(ModelForm):
    """To capture user preferences for specific animal species. To be used to as optional filters on animals by appearance

    Args:
        ModelForm (class): a base class provided by Flask-WTF-SQLAlchemy extension for creating forms that are automatically generated from SQLAlchemy models
    """

    # class Meta:
    #     model = UserAnimalAppearancePreferences

    breeds_preferences = SelectMultipleField(
        "", choices=[], default=False
    )

    animal_coat_preference = SelectMultipleField(
        "Animal Coat Preference",
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

    animal_coat_color_preference = SelectMultipleField(
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

    animal_age_preference = SelectMultipleField(
        "Animal Age Preference",
        choices=[
            ("baby", "baby"),
            ("young", "young"),
            ("adult", "adult"),
            ("senior", "senior"),
        ],
        default=["baby", "young", "adult", "senior"],
    )

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
            ('active', 'Active'),
            ('lazy', 'Lazy'),
            ('gentle', 'Gentle'),
            ('sweet', 'Sweet')
            # Add more choices as needed
        ],
        default=[],
    )

    animal_physical_attributes_preferences = SelectMultipleField(
        "Animal Physical Attributes Preferences",
        choices=[
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
            ("xlarge", "Extra Large"),
        ],
        default=["small", "medium", "large", "xlarge"],
    )

    gender_preference = SelectMultipleField(
        "Gender Preference",
        choices=[("male", "Male"), ("female", "Female")],
        default=["male", "female"],
    )
