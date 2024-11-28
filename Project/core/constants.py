# file to store constant variables that are necessary for app function and/or to be shared
import os

# keys to use to store key app values in Flask Session
CURR_USER_KEY = os.environ.get("CURR_USER_KEY", "curr_user")
CURR_ANIMALS_KEY = "ANIMAL_TYPES"
DEFAULT_LOCATION = "DEFAULT_LOCATION"
DISTANCE_KEY = "DISTANCE_PREF"
RESULTS_PER_PAGE_KEY = "RESULTS_PER_PAGE"
VIEWED_CONTENT_KEY = "VIEWED_CONTENT_LIST"
USER_LOCATION_KEY = "CURR_LOCATION"
NEXT_ANIMAL_URLS_KEY = "NEXT_URLS"
API_ANIMAL_TYPES_KEY = "API_ANIMAL_TYPES"
# key to use to store in session
LOCATION_SESSION_KEY = "location"

# Define limit for generator function to make API calls as PetFinder limits to 1000 calls per day
API_CALLS_PER_DAY = 1000
TIME_PERIOD = 86400  # Time period in seconds (86400 seconds = 24 hours)
MAX_TRIES = 3  # Maximum number of retries for handling RateLimitException



# default session keys
default_session_keys = {
    USER_LOCATION_KEY: os.environ.get(USER_LOCATION_KEY, "43.6429,-79.3889"),
    CURR_ANIMALS_KEY: os.environ.get(CURR_ANIMALS_KEY, ["dog"]),
    DEFAULT_LOCATION: {
        "geolocation": "43.6429,-79.3889",
        "state": "ON",
        "country": "CA",
        "postal_code": "m5j0b3",
        "city": "Toronto",
    },
    DISTANCE_KEY: 100,
    RESULTS_PER_PAGE_KEY: 6,  # default is 6 (so render 2 rows of 3 columns of cards)
    VIEWED_CONTENT_KEY: [],  # list of id of PetFinder API content seen by the user
}


# store default user_preference
default_animal_params = {
    "location": "Toronto,ON",
    "state": "ON",
    "country": "CA",
    "animal_types": [
        "dog"
    ],  # 8 possible values:  ‘dog’, ‘cat’, ‘rabbit’, ‘small-furry’, ‘horse’, ‘bird’, ‘scales-fins-other’, ‘barnyard’.
    "sort": "distance",
    "status": "adoptable,found",
    "distance": 100,
}
default_animal_types = [
    "dog",
    "cat",
    "rabbit",
    "small-furry",
    "horse",
    "bird",
    "scales-fins-other",
    "barnyard",
]

animal_emojis = {
    animal: emoji
    for animal, emoji in zip(
        default_animal_types, ["🐶", "🐱", "🐰", "🐹", "🐴", "🐦", "🦎", "🐄"]
    )
}
default_animal_status_choices = ["adoptable", "adopted", "found"]
default_animal_size_choices = ["small", "medium", "large", "xlarge"]
default_animal_age_choices = ["baby", "young", "adult", "senior"]
default_animal_gender_choices = ["male", "female", "unknown"]

default_error_details = {
    400: {
        "error_title": "400 Bad Request",
        "error_subtitle": "Oops! That's an invalid request.",
        "error_message": "The server couldn't understand your request. Please check your input and try again.",
        "redirect_url": "/",
        "redirect_text": "Back to Home",
    },
    401: {
        "error_title": "401 Unauthorized",
        "error_subtitle": "Access Denied",
        "error_message": "You don't have permission to access this resource. Please log in or check your credentials.",
        "redirect_url": "/login",
        "redirect_text": "Login",
    },
    403: {
        "error_title": "403 Forbidden",
        "error_subtitle": "Access Restricted",
        "error_message": "You don't have permission to access this resource.",
        "redirect_url": "/",
        "redirect_text": "Back to Home",
    },
    404: {
        "error_title": "404 Not Found",
        "error_subtitle": "Oops! Page not found.",
        "error_message": "The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.",
        "redirect_url": "/",
        "redirect_text": "Back to Home",
    },
    500: {
        "error_title": "500 Internal Server Error",
        "error_subtitle": "Oops! Something went wrong.",
        "error_message": "We're experiencing some technical difficulties. Please try again later or contact support if the problem persists.",
        "redirect_url": "/",
        "redirect_text": "Back to Home",
    },
}

default_animal_photos = {
    "dog": "dog-freepik.png",
    "cat": "cat-freepik.png",
    "horse": "horse-freepik.png",
    "bird": "bird-eucalyp.png",
    "small-furry": "small-furry-freepik.png",
    "scales-fins-other": "scales-smashicons.png",
    "barnyard": "scales-smashicons.png",
    "rabbit": "rabbit-freepik.png",
    "misc": "tracks_freepik.png",
}

default_animal_prefs = [
    {"declawed": False},
    {"shots_current": False},
    {"special_needs": False},
    {"spayed_neutered": False},
    {"house_trained": False},
    {"child_friendly": False},
    {"dogs_friendly": False},
    {"cats_friendly": False},
    {"breeds": ["any"]},
    {"colors": ["any"]},
    {"coat": ["any"]},
    {"age": ["any"]},
    {"gender": ["any"]},
    {"size": ["any"]},
    {"personality": ["any"]},
]
default_animal_status = "adoptable,found"
animal_colors = {
    "dog": "primary",
    "cat": "secondary",
    "rabbit": "success",
    "small-furry": "danger",
    "horse": "warning",
    "bird": "info",
    "scales-fins-other": "light",
    "barnyard": "dark",
}

IMAGE_FOLDER = os.path.join("static", "images", "graphics")
