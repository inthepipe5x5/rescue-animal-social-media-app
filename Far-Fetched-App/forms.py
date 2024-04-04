from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length
from wtforms_alchemy import model_form_factory
from models import (
    db,
    User,
    UserAnimalBehaviorPreferences,
    UserAnimalAppearancePreferences,
)


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


class UserEditForm(ModelForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[Length(min=6)])
    image_url = TextAreaField("(Optional) Image URL")
    location = StringField(
        "Location (Country, state/province, city OR postal code)",
        validators=[DataRequired()],
    )
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

    location = StringField(
        "Please Enter Your Location (Country, state/province, city OR postal code)",
        validators=[DataRequired()],
    )

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
    requested_animal_types = SelectMultipleField(
        "What kind of animal rescue are you interested in? Select the animals you want to search for",
        choices=[
            (str_key, emoji_value)
            for str_key, emoji_value in animal_type_emojis.items()
        ],
        coerce=str,
    )


class SpecificAnimalBehaviorPreferenceForm(ModelForm):
    """To capture user preferences for specific animal species. To be used to as optional filters on animals by behaviour

    Args:
        ModelForm (_type_): _description_
    """

    class Meta:
        model = UserAnimalBehaviorPreferences


class SpecificAnimalAppearancePreferenceForm(ModelForm):
    """To capture user preferences for specific animal species. To be used to as optional filters on animals by appearance

    Args:
        ModelForm (_type_): _description_
    """

    class Meta:
        model = UserAnimalAppearancePreferences
