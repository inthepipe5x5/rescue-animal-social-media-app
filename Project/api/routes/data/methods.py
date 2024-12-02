from flask import current_app, session
import json
import os
from Project.services import pf as api


def seed_animal_info():
    """Make API call for animal types information and save it to session and environment."""
    API_ANIMAL_TYPES_KEY = "API_ANIMAL_TYPES"
    with current_app.app_context().push():
        # Retrieve type list from session or environment
        type_list = (
            session.get(API_ANIMAL_TYPES_KEY)
            or json.loads(os.environ.get(API_ANIMAL_TYPES_KEY, "[]"))
            or None
        )

        if (
            not type_list
            and API_ANIMAL_TYPES_KEY not in session
            and API_ANIMAL_TYPES_KEY not in os.environ
        ):
            # make API call if
            type_list = api.seed_animal_types()

            # Store the type_list in session and environment
            session[API_ANIMAL_TYPES_KEY] = type_list
            os.environ[API_ANIMAL_TYPES_KEY] = json.dumps(type_list)
