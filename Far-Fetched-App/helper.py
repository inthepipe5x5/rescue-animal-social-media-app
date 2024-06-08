import json
import os
from dotenv import load_dotenv

from sqlalchemy.exc import NoResultFound  # type: ignore
from models import db, User, UserLocation, UserAnimalPreferences
from PetFinderAPI import PetFinderPetPyAPI

load_dotenv()
CURR_USER_KEY = os.environ.get("CURR_USER_KEY", "curr_user")


# Helper functions
def get_anon_preference(key, session, g):
    """Get saved ANON user preferences for a specific key.

    Returns: saved preferences in session, g, pf_api.default_options_obj or env var
    """
    if key in session:
        return session.get(key)
    elif key in g:
        return g.get(key)
    elif key in pf_api.default_options_obj:
        return pf_api.default_options_obj.get(key)
    else:
        print(f"No saved preference found for {key}: default anon preferences returned")
        env_key = "CURR_LOCATION" if key == "location" else key
        anon_pref = os.environ.get(env_key, pf_api.default_options_obj.get(key))
        return anon_pref


def get_user_preference(key, session, g):
    """Get saved logged-in user preferences for a specific key.
    # Implement logic to retrieve user preferences from the database
    # Return default value if preferences not found
    """
    if not CURR_USER_KEY in session:
        return get_anon_preference(key=key, session=session, g=g)
    else:
        u_id = session[CURR_USER_KEY]
    # dict for routing db queries based on key param
    db_q_dict = {
        "country": db.session.query(UserLocation.user_id == u_id).first().country,
        "animal_types": db.session.query(User.id == u_id).first().animal_types,
        "location": db.session.query(UserLocation.user_id == u_id).first(),
        "state": db.session.query(UserLocation.user_id == u_id).first().state,
    }

    # handle if key is 'country'
    db_query = db_q_dict[key]
    if key not in db_q_dict:
        db_query = db.session.query(UserAnimalPreferences.user_id == u_id).join()
        if NoResultFound:
            return TypeError(
                {
                    "status": 500,
                    "message": "Invalid key to fetch logged in user preferences",
                }
            )
    # handle no db results found
    if not db_query:
        if key in session:
            # return g.key and update user_preferences
            update_user_preferences({key: {"data": session.get(key)}})
            return session.get(key)
        elif key in g:
            # return g.key and update user_preferences
            update_user_preferences({key: {"data": g.get(key)}})
            return g.get(key)
    else:
        # return default key preference value if none found in db, session nor g
        env_key = "CURR_LOCATION" if key == "location" else key
        u_pref = os.environ.get(env_key, pf_api.default_options_obj.get(key))
        print(f"No saved preference found for {key}: default returned: {u_pref}")
        return u_pref


def update_anon_preferences(form, session):
    """Update ANON preferences from form data."""
    state = (
        form.state.data
        if form.state.data
        else pf_api.default_options_obj.get(
            "state", ",".split(os.environ.get("CURR_LOCATION"))[0]
        )
    )
    country = (
        form.country.data
        if form.country.data
        else pf_api.default_options_obj.get(
            "country", ",".split(os.environ.get("CURR_LOCATION"))[1]
        )
    )

    # handle form.animal_types.data
    if form.animal_types.data:
        # check if result is string or list
        # if string -> put into a list
        # if list, grab 1st item as anon users can only have 1 value in list saved only
        animal_types = (
            form.animal_types.data[:1]
            if isinstance(form.animal_types.data, list)
            else [form.animal_types.data]
        )
    if not form.animal_types.data:
        animal_types = (
            form.animal_types.data
            if form.animal_types.data
            else pf_api.default_options_obj.get(
                "animal_types", os.environ.get("ANIMAL_TYPES"), ["dog"]
            )
        )

    # update session
    session["CURR_LOCATION"] = ",".join(state, country)
    session["animal_types"] = animal_types

    


def update_user_preferences(form, session, user_obj):
    """Update logged-in user preferences from form data.
    # Implement logic to update user preferences in the database
    # Update session and global variables accordingly
    """
    # check if user logged in, else return update_anon_preferences function instead
    if not user_obj:
        return update_anon_preferences(form=form, session=session)
    else:
        # assign form data to variables
        state_data = form.state.data
        country_data = form.country.data
        location_data = form.location.data or ",".join(state_data, country_data)
        animal_types_data = form.animal_types.data

        if state_data or country_data or location_data:
            # save form data to session
            session["CURR_LOCATION"] = location_data
            # saving location form data to db
            user_location = UserLocation.query.filter_by(user_id=user_obj.id).first()
            if user_location:
                # update user_location with form data via object
                location_obj = user_location.update(
                    {"state": state_data, "country": country_data}
                )
                user_location.populate_by_obj(location_obj)
                db.session.add(user_location)
            else:
                user_location = UserLocation(
                    **{"state": state_data, "country": country_data}
                )
                db.session.add(user_location)
            db.session.commit()
        elif animal_types_data:
            # save form data to session
            session["animal_types"] = animal_types_data

            # save new user preferences to the database
            user = User.query.get_or_404(id=user_obj.id)
            user.animal_types = animal_types_data
            db.session.add(user)
            db.session.commit()

        # update global Flask app variables after committing to db
        update_global_variables()


def add_user_to_g(session, g):
    """Add current user to 'g'."""
    if CURR_USER_KEY in session:
        g.user = User.query.get_or_404(session[CURR_USER_KEY])
    else:
        g.user = None


def add_animal_types_to_g(session, g):
    """Add animal types preferred by the user to 'g'."""
    key = "animal_types"
    if key in session:
        g.animal_types = session[key]
    else:
        # check if user logged in
        user = g.user if CURR_USER_KEY in session else None
        # grab default animal_types
        g.animal_types = get_user_preference(key=key, session=session, user=user) if user else get_anon_preference(key=key, session=session, g=g)


def add_location_to_g(session, g):
    """Add CURR_LOCATION to 'g' and session
    Updates the CURR_LOCATION in session to give the app a location context for all API queries
    Does not return anything.
    """
    key = "location"

    # grab any saved location preference using helper function (will return anon_preference results if not logged in)
    location = get_user_preference(key=key, session=session, g=g)

    # update session and g
    session["CURR_LOCATION"] = location
    g.location = location


def get_init_api_data(session, g):
    """Function to populate session with API data in between requests to simulate "live" API data updates to Jinja templates that make use of it"""
    if "api_data" not in session:
        animal_types = (
            get_user_preference(key="animal_types")
            if "CURR_USER_KEY" in session
            else get_anon_preference(key="animal_types", session=session, g=g)
        )
        country = (
            get_user_preference(key="country")
            if "CURR_USER_KEY" in session
            else get_anon_preference(key="country", session=session, g=g)
        )
        raw_data = pf_api.get_animals_as_per_user_preferences(
            session=session, animal_types=animal_types, country=country
        )
        parsed_data = pf_api.parse_api_animals_data(api_data=raw_data)

        return json.dumps({"api_data": parsed_data})

    if "top_results" not in session:
        session["top_results"] = pf_api.get_top_results(parsed_data=parsed_data)

    else:
        return json.dumps({session.get(key) for key in ["top_results", "api_data"]})


pf_api = PetFinderPetPyAPI(
    get_anon_preference_func=get_anon_preference,
    get_user_preference_func=get_user_preference,
)
