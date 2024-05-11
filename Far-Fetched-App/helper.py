import json
import os
from dotenv import load_dotenv
from flask import session, g

from sqlalchemy.exc import NoResultFound # type: ignore
from models import db, User, UserLocation, UserAnimalPreferences
from PetFinderAPI import PetFinderPetPyAPI


load_dotenv()
CURR_USER_KEY = os.environ.get("CURR_USER_KEY", "curr_user")


# Helper functions
def get_anon_preference(key, session=session):
    """Get saved ANON user preferences for a specific key."""
    if key in session:
        return session.get(key)
    elif key in g:
        return g.get(key)
    elif key in pf_api.default_options_obj:
        return pf_api.default_options_obj.get(key)
    else:
        return os.environ.get(key)

def get_user_preference(key, session=session):
    """Get saved logged-in user preferences for a specific key.
    # Implement logic to retrieve user preferences from the database
    # Return default value if preferences not found
    """
    #dict for routing db queries based on key param
    db_q_dict = {'country': db.session.query(UserLocation.user_id == g.user.id).first().country,
                'animal_types': db.session.query(User.id == g.user.id).first().animal_types,
                'location': db.session.query(UserLocation.user_id == g.user.id).first(),
                'state':  db.session.query(UserLocation.user_id == g.user.id).first().state}
    
    #handle if key is 'country'
    db_query = db_q_dict[key]
    if key not in db_q_dict:
        return TypeError({"status": 500, "message": "Invalid key to fetch logged in user preferences"})
    #handle no db results found
    if not db_query:
        if key in session:
            #return g.key and update user_preferences
            update_user_preferences({key: {"data": session.get(key)}})
            return session.get(key)
        elif key in g:
            #return g.key and update user_preferences
            update_user_preferences({key: {"data": g.get(key)}})
            return g.get(key)
    else:
        # return default key preference value if none found in db, session nor g
        return pf_api.default_options_obj[key] 


def update_anon_preferences(form, session=session):
    """Update ANON preferences from form data."""
    if form.country.data:
        session['country'] = form.country.data
    if form.animal_types.data:
        session['animal_types'] = form.animal_types.data[:1] if isinstance(form.animal_types.data, list) else [form.animal_types.data]
    update_global_variables()

def update_user_preferences(form, session=session):
    """Update logged-in user preferences from form data.
    # Implement logic to update user preferences in the database
    # Update session and global variables accordingly
    """
    #save form data to session
    session['country'] = form.country.data
    session['animal_types'] = form.animal_types.data
    
    # saving location form data to db
    user_location = UserLocation.query.filter_by(user_id=g.user.id).first()
    if user_location:
        user_location.country = session['country']
        db.session.add(user_location)
    else:
        user_location = UserLocation(country=form.country.data)
        db.session.add(user_location)
    db.session.commit()
    
    #save new user preferences to the database
    user = User.query.get_or_404(id=g.user.id)
    user.animal_types = form.animal_types.data
    session[CURR_USER_KEY] = user.id
    db.session.add(user)
    db.session.commit()

    #update global Flask app variables after committing to db
    update_global_variables()


def add_user_to_g(session=session):
    """Add current user to 'g'."""
    if CURR_USER_KEY in session:
        g.user = User.query.get_or_404(session[CURR_USER_KEY])
    else:
        g.user = None

def add_animal_types_to_g(session=session):
    """Add animal types preferred by the user to 'g'."""
    if 'animal_types' in session:
        g.animal_types = session['animal_types']
    else:
        g.animal_types = ['dog']  # Default for anon users

def add_country_to_g(session=session):
    """Add country to 'g'."""
    if 'country' not in session:
        country = 'CA'  # Default country
        session['country'] = country
    else:
        country = session['country']

    g.country = country

    if CURR_USER_KEY in session:
        try:
            user_location = UserLocation.query.filter_by(user_id=session[CURR_USER_KEY].id).first()
            if user_location:
                country = user_location.country
            else:
                country = 'CA'  # Default
        except NoResultFound:
            country = 'CA'  # Default

        session['country'] = country
        g.country = country

def get_init_api_data(session=session):
    """Function to populate session with API data in between requests to simulate "live" API data updates to Jinja templates that make use of it
    """
    if "api_data" not in session:
        animal_type = get_user_preference(key='animal_type') if 'CURR_USER_KEY' in session else get_anon_preference(key='animal_type')
        country = get_user_preference(key='country') if 'CURR_USER_KEY' in session else get_anon_preference(key='country')
        raw_data = pf_api.get_animals_as_per_user_preferences(
            session=session, animal_type=animal_type, country=country
        )
        parsed_data = pf_api.parse_api_data(api_data=raw_data)
        
        return json.dumps({"api_data":parsed_data})
    
    if "top_results" not in session:
        session['top_results'] = pf_api.get_top_results(parsed_data=parsed_data)
    
    else:
        return json.dumps({session.get(key) for key in ['top_results', 'api_data']})
        
def update_global_variables():
    """Update global variables before each request."""
    add_country_to_g()
    add_animal_types_to_g()
    add_user_to_g()

pf_api = PetFinderPetPyAPI(get_anon_preference_func=get_anon_preference, get_user_preference_func=get_user_preference)
