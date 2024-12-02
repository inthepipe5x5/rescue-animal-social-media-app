import json
import os
from dotenv import load_dotenv

from sqlalchemy.exc import NoResultFound  # type: ignore

from Project.core.extensions import db
from Project.core.constants import default_animal_params
from Project.models import User, UserLocation, UserAnimalPreferences

load_dotenv()
CURR_USER_KEY = os.environ.get("CURR_USER_KEY", "curr_user")


# Helper functions
def get_anon_preference(key, session, g):
    """Get saved ANON user preferences for a specific key.

    Returns: saved preferences in session, g, default_animal_params or env var
    """
    if key in session:
        return session.get(key)
    elif key in g:
        return g.get(key)
    elif key in default_animal_params:
        return default_animal_params.get(key)
    else:
        print(
            f"No saved Anon User preference found for {key}: default anon preferences returned"
        )
        env_key = "CURR_LOCATION" if key == "location" else key
        anon_pref = os.environ.get(env_key, default_animal_params.get(key))
        return anon_pref


def get_user_preference(key, session, g):
    """Get saved logged-in user preferences for a specific key.

    # Example usage:
        > user_pref = get_user_preference("location", session, g)
        > print(user_pref)
    """

    if CURR_USER_KEY not in session:
        return get_anon_preference(key=key, session=session, g=g)

    u_id = session[CURR_USER_KEY]

    def db_query_helper(pref_key, matching_user_id):
        """Helper function to query db.session depending on pref_key passed in."""
        # Dict for routing db queries based on key param
        model_dict = {
            "country": UserLocation,
            "animal_types": UserAnimalPreferences,
            "location": UserLocation,
            "state": UserLocation,
        }
        if not pref_key:
            raise TypeError(
                f"Bad key argument passed into db_query_helper func call {pref_key}"
            )

        model = model_dict.get(pref_key)
        if model:
            try:
                if pref_key == "animal_types":
                    result = db.session.query(model).filter_by(user_id=matching_user_id)
                else:
                    result = (
                        db.session.query(model)
                        .filter_by(user_id=matching_user_id)
                        .first()  # add .first() method as non-animal_types queries will be singular result where animal_types will expect a list
                    )

                if result:
                    return result
                else:
                    raise NoResultFound
            except NoResultFound:
                if key in session:
                    # return g.key and update user_preferences
                    update_user_preferences({key: {"data": session.get(key)}})
                    return session.get(key)
                elif key in g:
                    # return g.key and update user_preferences
                    update_user_preferences({key: {"data": g.get(key)}})
                    return g.get(key)
                else:
                    return None
        else:
            return None

    db_query = db_query_helper(pref_key=key, matching_user_id=u_id)

    if db_query is None:
        # Return default key preference value if none found in db, session nor g
        env_key = "CURR_LOCATION" if key == "location" else key
        u_pref = os.environ.get(env_key, default_animal_params.get(key))
        print(f"No saved preference found for {key}: default returned: {u_pref}")
        return u_pref
    else:
        return db_query


def update_anon_preferences(form, session):
    """Update ANON preferences from form data."""
    state = (
        form.state.data
        if form.state.data
        else default_animal_params.get(
            "state", ",".split(os.environ.get("CURR_LOCATION"))[0]
        )
    )
    country = (
        form.country.data
        if form.country.data
        else default_animal_params.get(
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
            else default_animal_params.get(
                "animal_types", os.environ.get("ANIMAL_TYPES"), ["dog"]
            )
        )

    # update session
    session["CURR_LOCATION"] = ",".join(state, country)
    session["animal_types"] = animal_types
    # Ensure the session is marked as modified
    session.modified = True


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
            # Ensure the session is marked as modified
            session.modified = True
            # save new user preferences to the database
            user = User.query.get_or_404(id=user_obj.id)
            user.animal_types = animal_types_data
            db.session.add(user)
            db.session.commit()

        # # update global Flask app variables after committing to db
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
        if CURR_USER_KEY in session:
            # grab default animal_types
            g.animal_types = get_user_preference(key=key, session=session, g=g)
        else:
            g.animal_types = get_anon_preference(key=key, session=session, g=g)


def add_location_to_g(session, g):
    """Add CURR_LOCATION to 'g' and session
    Updates the CURR_LOCATION in session to give the app a location context for all API queries
    Does not return anything.
    """
    key = "location"

    # grab any saved location preference using helper function (will return anon_preference results if not logged in)
    location = get_user_preference(key=key, session=session, g=g)
    # handle if location is an db.Model Object instance
    if isinstance(location, db.Model):
        location = location.city_state_country_str()
    if isinstance(location, str):
        location = location
    # update session and g
    session["CURR_LOCATION"] = location
    g.location = location


# @data_bp.before_request
def update_global_variables(session, g):
    """Update global variables before each request."""

    add_location_to_g(session=session, g=g)
    add_animal_types_to_g(session=session, g=g)
    add_user_to_g(session=session, g=g)
