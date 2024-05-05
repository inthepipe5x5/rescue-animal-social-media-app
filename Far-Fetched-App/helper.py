from sqlalchemy.exc import NoResultFound
from app import app, session, CURR_USER_KEY, g
from models import db, User, UserLocation, UserAnimalPreferences
from PetFinderAPI import pf_api
# HELPER FUNCTIONS FOR PREFERENCE ROUTES
def get_anon_preferences(key):
    """get saved ANON user preferences for a specific key 
    
    key param = STRING eg. 'country'
    """
    #handle invalid key param
    if key not in pf_api:
        return TypeError({"status": 500, "message": "Invalid key to fetch anon user preferences"})
    else:
        with app.app_context():
            if key in session:
                print(f"found {key} in session: {session[key]}")
                return session[key]
            elif key in g:
                print(f"found {key} in g: {g[key]}")
                return g[key]
            else:
                #return default user preference param
                print(f'no anon preferences found for {key}, default preferences returned')
                return pf_api.default_options_obj[key]

def get_user_preference(key):
    """get saved ANON user preferences for a specific key 
    
    key param = STRING eg. 'country'
    
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
    if not db_query:
        if key in session:
            #return g.key and update user_preferences
            update_user_preferences({key: {"data": session[key]}})
            return session[key]
        elif key in g:
            #return g.key and update user_preferences
            update_user_preferences({key: {"data": g[key]}})
            return g.get(key)
    else:
        # return default key preference value if none found in db, session nor g
        return pf_api.default_options_obj[key] 

        
def update_anon_preferences(form):
    """Helper function to set ANON preferences from form

    Args:
        form (_type_): _description_
        """
    with app.app_context():
        session['country'] = form.country.data
        if 'animal_types' in session:
            if isinstance(form.animal_types.data, str):
                session['animal_types'] = [form.animal_types.data][:1] #save STR value of form to list and slice and return just first value in list
            elif isinstance(form.animal_types.data, list): #check if list or string
                session['animal_types'] = form.animal_types.data[:1] #only save the first value of the list for anon users
        update_global_variables()

def update_user_preferences(form):
    """Helper function to SAVE user preferences for LOGGED-IN users to DB & update Flask sessions"""
    with app.app_context():
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

def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get_or_404(session[CURR_USER_KEY])
    else:
        g.user = None
        
def add_animal_types_to_g():
    """Add the animal types preferred by the user to 'g'"""
    #if logged in user, set session['animal_types'] to the saved LIST in DB
    if CURR_USER_KEY in session :
        # Get animal types selected by the user from the previous form submission
        user_pref = UserAnimalPreferences.get_or_404(
            UserAnimalPreferences.user_id == session[CURR_USER_KEY]
        )
        if user_pref: 
            session['animal_types'] = user_pref 
    else:
        #default for anon users
        #default for logged in users with no saved preferences 
        session['animal_types'] = ['dog'] 

    
def add_country_to_g():
    if 'country' not in session:
        country = 'CA'  # set default country
        session['country'] = country
    else:
        country = session['country']

    g.country = country  # set country in global context

    # check if user is logged in
    if CURR_USER_KEY in session:
        try:
            user_location = UserLocation.query.filter_by(user_id=session[CURR_USER_KEY].id).first()
            if user_location:
                country = user_location.country
            else:
                country = 'CA'  # set default
        except NoResultFound:
            country = 'CA'  # set default

        session['country'] = country
        g.country = country


def update_global_variables():
    """Update global variables after saving user preferences."""
    add_country_to_g()
    add_animal_types_to_g()
    add_user_to_g()

