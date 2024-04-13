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
    # UserAnimalBehaviorPreferences,
    # UserAnimalAppearancePreferences,
    UserLocation,
    UserTravelPreferences
)
# from PetFinderAPI import pf_api


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

    class Meta:
        model = User
        exclude=['rescue_action_type', 'registration_date']
        
    
    # location = StringField(
    #     "Please Enter Your Location (Country, state/province, city OR postal code)",
    #     validators=[DataRequired()],
    # )


class MandatoryOnboardingForm(FlaskForm):
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
        "scales-fins-other": "🐠 Scales, Fins, Other",
        "barnyard": "🐄 Barnyard",
    }

    # Define the SelectMultipleField with the emoji labels
    animal_types = SelectMultipleField(
        "What kind of animal rescue are you interested in? Select the animals you want to search for",
        choices=[
        (str_value, emoji_key)
        for str_value, emoji_key in animal_type_emojis.items()
        ],
        coerce=str, default=['dog', 'cat'], validators=[DataRequired()]
    )

    #Rescue Action Type
    rescue_action_type = SelectMultipleField(
        "Select all the aspects of animal rescue you want to get involved in", 
        choices=[
        ('volunteer', 'Looking to Volunteer'),
        ('foster', 'Animal Fostering'),
        ('adopter', 'Looking to Adopt'),
        ('donation', 'Donation')
        ], 
    coerce=str, default=['volunteer', 'foster', 'adopter','donation']
    )
    

# class userSearchOptionsPreferencesForm(BaseUserForm):
#     """Form to capture user preferences for specific animal traits: behavior, medical history, physical traits
#     If none, user prefers to omit during search process. Intended to be linked to UserPreferences or

#     Args:
#         ModelForm (class): a base class provided by Flask-WTF-SQLAlchemy extension for creating forms that are automatically generated from SQLAlchemy models
#     """

    # behavior_medical_bool = BooleanField(
    #     "Search by animal behavior or medical history?", default=False
    # )
    # # behavior options

    # # breeds
    # breeds_preference_bool = BooleanField(
    #     "Searching for specific breeds?", default=False
    # )

    # # physical traits
    # appearance_bool = BooleanField("Search by physical traits?", default=False)

class UserEditForm(ModelForm):
    # class Meta:
    #     model=User
        
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[Length(min=6)])
    image_url = TextAreaField("(Optional) Image URL")
    location = StringField(
        "Location (Country, state/province, city OR postal code)",
        validators=[DataRequired()],
    )
    bio = TextAreaField("(Optional) Tell me about yourself!")

class UserLocationForm(ModelForm):
    """Form for adding user location information"""
    class Meta:
        model=UserLocation

class UserTravelForm(ModelForm):
    """Optional form for adding user travel preferences"""
    class Meta:
        model=UserTravelPreferences

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
