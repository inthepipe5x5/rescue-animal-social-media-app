from flask import (  # type: ignore
    Flask,
    render_template,
    request,
    flash,
    redirect,
    session,
    g,
    url_for,
    jsonify,
)

from flask_login import (
    login_required,
    login_user,
    logout_user,
    current_user,
)
from dotenv import load_dotenv  # type: ignore
import os
import pycountry
from time import sleep
import json
from urllib.parse import urljoin

# from functools import wraps #TODO: to protect certain API routes
from werkzeug.exceptions import HTTPException

# from marshmallow import MarshMallow

from Project.core.methods import get_anon_location
from core import (
    default_session_keys,
    CURR_ANIMALS_KEY,
    DEFAULT_LOCATION,
    DISTANCE_KEY,
    RESULTS_PER_PAGE_KEY,
    VIEWED_CONTENT_KEY,
    USER_LOCATION_KEY,
    NEXT_ANIMAL_URLS_KEY,
    API_ANIMAL_TYPES_KEY,
    animal_colors,
    active_authenticated_user
)

from Project.models import (
    db,
    User,
    UserLocation,
    UserAnimalPreferences,
    UserTravelPreferences,
    UserFavorites,
)

from forms import (
    UserAddForm,
    LoginForm,
    UserEditForm,
    UserExperiencesForm,
    UserLocationForm,
    AnonExperiencesForm,
    SpecificAnimalPreferencesForm,
    HiddenForm,
    HiddenLocationForm,
    UserTravelForm,
)
from services.petfinder.helper import (
    data_bp,
    get_anon_preference,
    get_user_preference,
    update_anon_preferences,
    update_user_preferences,
    update_global_variables,  # currently in helper.py
    add_user_to_g,
    add_location_to_g,
    add_animal_types_to_g,
)
from .api.routes.pf.pf_bp import mock_pf_bp

from config import config, Config
from services import pf as api
from Project.utils.parse import Parse

# import custom exceptions
from services.petfinder.api_exceptions import (
    PetFinderResourceNotFoundError,
    PetFinderInvalidCredentialsError,
    PetFinderAccessDeniedError,
    PetFinderInvalidParametersError,
    PetFinderLocationError,
    PetFinderUnexpectedServerError,
)
from services.petfinder.petfinder_types import (
    AnimalReqParams,
    AnimalType,
    AnimalTypes,
    FormattedAnimalType,
)



load_dotenv()

# create Flask app
app = Flask(__name__)
# app.session_interface = CustomSessionInterface()
# Register blueprint
app.register_blueprint(mock_pf_bp)

# create config instance
app_config_instance = Config()

# config Flask app
flask_env_type = (
    os.environ.get("FLASK_ENV")
    if os.environ.get("FLASK_ENV") is not None
    else "default"
)

app_config_instance.config_app(app=app, obj=config[flask_env_type])  # type: ignore
# app = create_app()

# Inject Custom Jinja filters Here
custom_filters_dict = {
    "format_kebob_case": Parse.format_kebob_case,
    "prettify_animal_types": Parse.prettify_animal_types,
}
for function_key, function in custom_filters_dict.items():
    app.jinja_env.filters[function_key] = function


# # petpy instance
# petpy = Petfinder(key=os.environ.get("API_KEY"), secret=os.environ.get("API_SECRET"))

# # set auth in petpy
# if not petpy._auth:
#     petpy._auth = os.environ.get("ACCESS_TOKEN", None)

##############################################################################
# SESSION FUNCTIONS

# class CustomSession(dict, SessionMixin):
#     """Custom Session Interface to handle session management by expanding beyond the basic dictionary functionality of Flask Session
#     Args:
#         dict (_type_): Python Dictionary
#         SessionMixin (_type_): Mixin from Flask Session that expands the default session object in Flask
#     """

#     def init_default_session():
#         """Initialize the session with default values"""
#         for key, value in default_session_keys.items():
#             session.setdefault(key, value)
#         session.new = True
#         session.modified = True

#     def init_session(self):
#         """Initialize the session with USER if user values else populates with default values"""

#         #populate with default for anon-users
#         if not active_authenticated_user():
#             return self.init_default_session()
#         else:
#             user_id=current_user.id
#             user_session_data = get_user_data(user_id=user_id)
#             if user_session_data:
#                 #update session with state_country, animal_types, curr_location, distance
#                 session.update(user_session_data)


#     def reset_session(self):
#         """Reset the session to default values"""
#         self.clear()
#         self.init_session()

# class CustomSessionInterface(SessionInterface):
#     def open_session(self, app, request):
#         session = CustomSession()
#         session.init_session()
#         app.logger.info(f"Session initialized - {session}")
#         return session

#     def reset_session(self, app, session):
#         session.reset_session()
#         app.logger.info(f"Session reset to default - {session}")

##############################################################################
# User signup/login/logout

# TODO: REMOVE LATER AS I'M USING THE SAME FUNCTION FROM FLASK-LOGIN INSTEAD
# def login_required(route_func):
#     @wraps(route_func)
#     def protected_route(*args, **kwargs):
#         if CURR_USER_KEY not in session:
#             # flash error
#             flash("Unauthorized", "danger")
#             # not authenticated, redirect to login and then requested url once authenticated
#             return redirect(url_for("login"), next=request.url)
#         # else the user is authenticated and should be allowed to proceed to the protected route
#         return route_func(*args, **kwargs)

#     return protected_route


# def require_api_key(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         api_key = request.headers.get("X-API-Key")
#         if api_key and api_key == os.environ.get("SECRET_KEY"):
#             return f(*args, **kwargs)
#         else:
#             abort(401)  # Unauthorized

#     return decorated_function




##############################################################################


# TODO # FIX LATER
# @app.route("/static/images/graphics/<path:filename>")
# def serve_image(filename):
#     return send_from_directory(IMAGE_FOLDER, f"/{filename}")






@app.route("/discover/animals", methods=["GET"])
def discover_animals():
    """Route to fetch and display paginated animal data, with error handling and fallback UI in case of API downtime."""

    user = current_user._get_current_object() if active_authenticated_user() else None

    # Determine user location
    location_data = None

    # Get location from user's serialized data
    location_data = user.serialize().get("location") if user else get_anon_location()
    if not location_data:
        return redirect(url_for("form_users_location"))

    init_params = create_init_params(req_type="animals")
    animal_types = (
        request.args.get("animal_type")
        or init_params.get("type")
        or user.get("animal_types")
        or session.get("ANIMAL_TYPES", ["dog"])
    )
    target_count = int(
        request.args.get("limit")
        or session.get(RESULTS_PER_PAGE_KEY)
        or init_params.get("limit", 9)
    )  # Number of animals per page

    # Prepare exclude_ids for viewed or favorited animals
    user_favorites = user.get_all_favorites if user else []
    viewed_content = session.get("VIEWED_CONTENT_LIST", [])
    exclude_ids = set(viewed_content + user_favorites)

    # Flatten user preferences for API request
    flattened_animal_preferences = (
        api.preprocess_preferences(
            init_params=init_params.copy(),
            prefs_obj=get_user_animal_preferences(species_list=animal_types),
        )
        if user
        else {animal_type: None for animal_type in animal_types}
    )

    # Ensure animal_types is always a list
    animal_types = [animal_types] if isinstance(animal_types, str) else animal_types

    next_urls = create_next_animal_url(animal_types=animal_types, endpoint="animals")

    render_content = []
    # try:

    while len(render_content) < target_count:
        session[NEXT_ANIMAL_URLS_KEY] = next_urls  # Save updated next URLs in session

        # Combine initial parameters with animal preferences and location if provided
        params = (
            init_params.copy().update(flattened_animal_preferences)
            if flattened_animal_preferences
            else init_params.copy()
        )

        # set params['location'] properly
        if location_data or isinstance(params.get("location"), (dict, object)):
            params["location"] = api.get_next_location(location_dict=location_data)

        for animal_type in animal_types:
            next_url = next_urls.get(animal_type) or urljoin(
                f"{api.BASE_API_URL}/animals", params
            )

            if not next_url:
                continue  # Skip this type if no next URL is available (exhausted)
            # Fetch data from the API using request_with_retry
            results = api.request_with_retry(
                endpoint="animals", request_url=next_url, params=params
            )

        if not results:
            raise PetFinderResourceNotFoundError()
            break  # Exit if generator returns no content

        # Filter and parse results
        filters = create_user_preference_filters()
        filtered_results, success_flag = api.filter_parse_animal_results(
            results, filter_prefs=filters
        )
        render_content.extend(filtered_results)

        # Add viewed content to session if successful
        if success_flag:
            session["VIEWED_CONTENT_LIST"] = list(
                set(
                    session.get("VIEWED_CONTENT_LIST", [])
                    + [result["id"] for result in filtered_results]
                )
            )
            break

    # No content message
    if len(render_content) == 0:
        flash(
            "No animals found matching your filters. Adjust filters or try again later!",
            "warning",
        )
        init_params = {"limit": target_count}

        # Attempt backup API call if no content
        try:
            backup_results = api._get_request(
                "animals", f"{api.BASE_API_URL}/animals", params=init_params
            )
            if not backup_results:
                return redirect(
                    url_for(
                        "custom_error",
                        error_title="PetFinder API Unavailable",
                        error_subtitle="We're sorry for the inconvenience.",
                        error_message="PetFinder's API is temporarily down. Please try again later.",
                    )
                )
            render_content = backup_results.get("animals", [])
        except Exception as api_error:
            app.logger.error(f"API Backup Call Failed: {api_error}")
            return redirect(
                url_for(
                    "custom_error",
                    error_title="PetFinder API Error",
                    error_subtitle="Unable to retrieve animals.",
                    error_message="Our system is currently experiencing issues connecting to PetFinder. Please try again later.",
                )
            )

        # except PetFinderAccessDeniedError as e:
        #         #wait attempt number of seconds in case of rate limiting
        #         sleep(int(attempt))
        #         #reset access token
        #         self._get_access_token()
        #         if attempt == max_retries:
        #             break
        #         else:
        #             continue
        #     except PetFinderInvalidParametersError as e:
        #         # Handle invalid parameters by removing problematic keys and retrying
        #         invalid_params = (
        #             e.invalid_params or []
        #         )  # Retrieve invalid params from error, if available
        #         for param in invalid_params:
        #             params.pop(param, None)  # Remove invalid key
        #         continue  # Retry request with modified parameters

        #     except PetFinderLocationError:
        #         # Handle location errors by cycling through alternative locations
        #         location_dict = params.get("location", {})
        #         while location_dict:
        #             next_location, location_dict = self.get_alternative_locations(
        #                 location_dict
        #             )

        #             if not next_location:
        #                 # All location alternatives have been exhausted; redirect user to enter location
        #                 return PetFinderLocationError(
        #                     error_title="Error determining location",
        #                     error_subtitle="Please set your location",
        #                     error_message=(
        #                         "Can't determine your location for local content. "
        #                         "Please enter your location or enable geolocation for more accurate results."
        #                     ),
        #                     redirect_url="/users/location",
        #                 ).error_info()

        #             # Update params with the new location and retry request
        #             params["location"] = next_location
        #             response = self._get_request(
        #                 endpoint,
        #                 request_url or f"{self.BASE_API_URL}/{endpoint}",
        #                 params=params,
        #             )
        #             self.log_and_raise_for_status(response)
        #             return response.json()  # Return if successful

        #     except RateLimitException:
        #         print("Rate limit reached. Retrying...")

        # # If max retries without success, raise a final error
        # raise Exception(f"Request to {endpoint} failed after {max_retries} retries.")

        # Respond with JSON for AJAX or render HTML
        if request.is_json:
            return jsonify(
                {"results": render_content, "success_flag": bool(render_content)}
            )

        return render_template("results.html", animals=render_content)

    # except Exception as e:
    #     app.logger.error(f"Error at endpoint {request.endpoint}: {e}")
    #     return redirect(
    #         url_for(
    #             "custom_error",
    #             error_title="Unexpected Error",
    #             error_subtitle="We ran into an issue!",
    #             error_message="Our system encountered an issue loading animals. Please try refreshing the page or come back later.",
    #         )
    #     )


# @app.route("/discover/animals", methods=["GET"])
# def discover_animals():
#     """Route to fetch and display paginated animal data, with error handling and fallback UI in case of API downtime."""

#     user = current_user._get_current_object() if active_authenticated_user() else None

#     # Determine user location
#     location_data = None
#     if user:
#         # Get location from user's serialized data
#         location_data = user.serialize().get("location")
#     else:
#         # Anonymous user, pull location from session
#         location_data = {
#             "city": session.get("city"),
#             "state": session.get("state"),
#             "postal_code": session.get("postal_code"),
#             "geolocation": session.get("geolocation"),
#         } or default_session_keys.get(DEFAULT_LOCATION)

#     init_params = create_init_params(req_type="animals")
#     animal_types = (
#         request.args.get("animal_type")
#         or init_params.get("type")
#         or user.get("animal_types")
#         or session.get("ANIMAL_TYPES", ["dog"])
#     )
#     target_count = int(
#         request.args.get("limit") or init_params.get("limit", 9)
#     )  # Number of animals per page

#     # Prepare exclude_ids for viewed or favorited animals
#     user_favorites = user.get_all_favorites if user else []
#     viewed_content = session.get("VIEWED_CONTENT_LIST", [])
#     exclude_ids = set(viewed_content + user_favorites)

#     # Flatten user preferences for API request
#     flattened_animal_preferences = (
#         api.preprocess_preferences(
#             init_params=init_params.copy(),
#             prefs_obj=get_user_animal_preferences(species_list=animal_types),
#         )
#         if user
#         else {animal_type: None for animal_type in animal_types}
#     )

#     # Ensure animal_types is always a list
#     animal_types = [animal_types] if isinstance(animal_types, str) else animal_types
#     next_urls = session.get(
#         NEXT_ANIMAL_URLS_KEY, {animal_type: None for animal_type in animal_types}
#     )

#     # Initialize generator with new parameters, including location
#     generator = api.animal_pagination_generator(
#         animal_types=animal_types,
#         target_count=target_count,
#         init_params=init_params,
#         next_urls=next_urls,
#         exclude_ids=exclude_ids,
#         flattened_animal_preferences=flattened_animal_preferences,
#         location_dict=location_data,
#     )

#     render_content = []
#     no_api_content = False

#     try:
#         for data in generator:
#             if "error" in data:
#                 # Flash the error message
#                 flash(
#                     f"Error fetching data for {data['animal_type']}: {data['error']}",
#                     "error",
#                 )
#                 # Optionally, append partial results if desired
#                 render_content.extend(data.get("partial_results", []))
#             else:
#                 # Accumulate full results
#                 render_content.extend(data)

#         while len(render_content) < target_count:
#             results, next_urls = next(generator)
#             session[NEXT_ANIMAL_URLS_KEY] = next_urls  # Save updated next URLs in session

#             if not results:
#                 no_api_content = True
#                 break  # Exit if generator returns no content

#             # Filter and parse results
#             filters = create_user_preference_filters()
#             filtered_results, success_flag = api.filter_parse_animal_results(
#                 results, filter_prefs=filters
#             )
#             render_content.extend(filtered_results)

#             # Add viewed content to session if successful
#             if success_flag:
#                 session["VIEWED_CONTENT_LIST"] = list(
#                     set(
#                         session.get("VIEWED_CONTENT_LIST", [])
#                         + [result["id"] for result in filtered_results]
#                     )
#                 )
#                 break

#         # No content message
#         if no_api_content:
#             flash(
#                 "No animals found matching your filters. Adjust filters or try again later!",
#                 "warning",
#             )
#             init_params = {"limit": target_count}

#             # Attempt backup API call if no content
#             try:
#                 backup_results = api._get_request(
#                     "animals", f"{api.BASE_API_URL}/animals", params=init_params
#                 )
#                 if not backup_results:
#                     return redirect(
#                         url_for(
#                             "custom_error",
#                             error_title="PetFinder API Unavailable",
#                             error_subtitle="We're sorry for the inconvenience.",
#                             error_message="PetFinder's API is temporarily down. Please try again later.",
#                         )
#                     )
#                 render_content = backup_results.get("animals", [])
#             except Exception as api_error:
#                 app.logger.error(f"API Backup Call Failed: {api_error}")
#                 return redirect(
#                     url_for(
#                         "custom_error",
#                         error_title="PetFinder API Error",
#                         error_subtitle="Unable to retrieve animals.",
#                         error_message="Our system is currently experiencing issues connecting to PetFinder. Please try again later.",
#                     )
#                 )

#         # Respond with JSON for AJAX or render HTML
#         if request.is_json:
#             return jsonify(
#                 {"results": render_content, "success_flag": bool(render_content)}
#             )

#         return render_template("results.html", animals=render_content)

#     except Exception as e:
#         app.logger.error(f"Error at endpoint {request.endpoint}: {e}")
#         return redirect(
#             url_for(
#                 "custom_error",
#                 error_title="Unexpected Error",
#                 error_subtitle="We ran into an issue!",
#                 error_message="Our system encountered an issue loading animals. Please try refreshing the page or come back later.",
#             )
#         )


@app.route("/loading")
def loading_route():
    """Route to render loading

    Returns:
        renders view with skeleton loading cards and then directs after 5 seconds
    """
    redirect_url = request.args.get("redirect_url") or url_for("home")
    redirect_interval = request.args.get("redirect_interval") or 5000

    return render_template(
        url_for("templates", filename="loading_view.html"),
        redirect_url=redirect_url,
        redirect_interval=redirect_interval,
    )

@app.route("/reseed_db", methods=["GET"])
def reseed_db():
    """
    recreate db
    """

    app.logger.info("recreating db by dropping & recreating tables")

    # drop and recreate all tables
    db.drop_all()
    db.create_all()

    test_user = {
        "username": "test123",
        "email": "test123@test123.com",
        "bio": "test123",
        "password": "test123",
        "animal_types": ["dog"],
        "image_url": "../static/images/profile-images/default-hero-sasha-sashina-YCsh4ltV9Ec-unsplash.jpg",
        "rescue_action_type": ["volunteering", "donation", "adoption", "animal foster"],
    }

    test_user_location = default_session_keys["DEFAULT_LOCATION"]

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
    # Creating a list of user preferences
    test_user_animal_prefs = [
        {
            "user_id": 1,  # assuming test123 id is "1"
            "species": test_user["animal_types"][0],
            "user_preference_name": list(pref.keys())[0],
            "user_preference_data": list(pref.values())[0],
        }
        for pref in default_animal_prefs
    ]

    # create user
    # test_user["password"] = bcrypt.generate_password_hash(
    #     password=test_user["password"]
    # ).decode("utf8")
    test123 = User.signup(**test_user)
    db.session.add(test123)
    db.session.commit()
    app.logger.info(f"created user: test123 {test123}")

    # create location
    test123_location = UserLocation(**test_user_location)
    db.session.add(test123_location)
    test123.location = test123_location
    db.session.commit()
    app.logger.info(f"created location: test123_location {test123_location}")

    # create prefs
    test123_prefs = db.session.bulk_insert_mappings(
        UserAnimalPreferences, test_user_animal_prefs
    )

    return jsonify(
        {
            "message": "database recreated and user test123 inserted",
            "user": {"id": test123.id, **test_user},
            "location": test_user_location,
            "animal_prefs": test_user_animal_prefs,
        }
    )


@app.route("/set_location", methods=["POST"])
def set_location():
    """Route to set location for search results

    Returns:
        _type_: _description_
    """
    # grab location from request body
    location = request.values.get(
        "location"
    )  # Use request.values for a combined view of query and form data.

    # handle lack of location provided from request body
    if not location:
        # check if country, state is provided in request body
        country = request.values.get("country", None)
        state = request.values.get("state", None)
        postal_code = request.values.get("postal_code", None)
        geolocation = request.values.get("geolocation", None)

        location = ",".join(country, state)

    # set location in session
    session[USER_LOCATION_KEY] = location

    success_msg = f"App.py: Current CURR_LOCATION set to: {session['CURR_LOCATION']}"
    add_location_to_g(session=session, g=g)

    return jsonify({"message": success_msg})


@app.route("/set_global", methods=["GET", "POST"])
def set_global():
    """Route to set the global options for country of origin and animal types

    If GET -> return form page
    If POST -> set 'country' and/or 'animal_types' in sessions

    """

    # Check if the user is logged in
    if active_authenticated_user():

        animal_types = (
            session.get("ANIMAL_TYPES")
            if "ANIMAL_TYPES" in session
            else current_user.animal_types
        )
        state_country = (
            session.get("STATE_COUNTRY", "ON, CA🍁")
            if "STATE_COUNTRY" in session
            else current_user.location.city_state_country_str()
        )

        form = UserExperiencesForm(animal_types=animal_types, country=country)
    else:
        # check db, session and 'g' for ANON preferences. if not found, will return default country : 'CA'
        country = get_anon_preference(key="country", session=session, g=g)
        animal_types = get_anon_preference(key="animal_types", session=session, g=g)
        form = AnonExperiencesForm(country=country, animal_types=animal_types)

    # Validate form submission
    if form.validate_on_submit():
        # Save preferences for logged-in users
        if "CURR_USER" in session:
            update_user_preferences(form=form)
            return redirect(url_for("home.html"))
        else:
            # Redirect anonymous users to login if animal types are selected
            if isinstance(form.animal_types.data, list):
                return redirect(url_for("login"))
            else:
                # Set global country and animal type for anonymous users
                update_anon_preferences(form=form)

    return render_template(
        "users/form.html", form=form, next=url_for("discover_animals")
    )


##############################################################################
# Homepage and error pages


@app.route("/")
def homepage():
    """Show homepage:"""

    offcanvas_form = UserExperiencesForm()

    if active_authenticated_user():
        # grab user
        user = current_user._get_current_object().serialize()
        user = user if user else load_user(user_id=current_user.id)

        # set session with user data
        load_session()

        return render_template("home.html", user=user, form=offcanvas_form)
    else:
        return render_template("home-anon.html")  # , results=results


##############################################################################


# Inject context into Jinja templates to ensure that Flask session and 'g' object is available without having to manually pass as param into every template
@app.context_processor
def inject_global_vars():
    """Injects the session and g objects into the Jinja2 template context"""
    # print('template context processor being called', session['CURR_USER'])
    return {
        "session": session,
        "g": g,
        "animal_types": api.animal_types,
        "animal_emojis": api.animal_emojis,
        "animal_colors": animal_colors,
        "animal_default_photos": {
            "dog": "dog-freepik.png",
            "cat": "cat-freepik.png",
            "horse": "horse-freepik.png",
            "bird": "bird-eucalyp.png",
            "small-furry": "small-furry-freepik.png",
            "scales-fins-other": "scales-smashicons.png",
            "barnyard": "scales-smashicons.png",
            "rabbit": "rabbit-freepik.png",
            "misc": "tracks_freepik.png",
        },
        "animal_border_colors": {
            key: "border-" + value for key, value in animal_colors.items()
        },
        "animal_bg_colors": {
            key: "bg-" + value for key, value in animal_colors.items()
        },
        "animal_btn_colors": {
            key: "btn-" + value for key, value in animal_colors.items()
        },
        "CURR_USER": (
            current_user._get_current_object()
            if (active_authenticated_user() and current_user)
            else None
        ),
        "user_auth_status": active_authenticated_user(),
        "default_prettified_animal_types": Parse.get_default_prettified_animal_types,
    }


# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask
@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers["Cache-Control"] = "public, max-age=0"
    return req


if __name__ == "__main__":
    flask_env = os.environ.get("FLASK_ENV", "development")
    app.logger.warning(f"Starting app with FLASK_ENV={flask_env}")

    # #for testing / dev purposes, drop and recreate the db tables
    # db.drop_all()
    # db.create_all()

    # run app
    if flask_env == "production":
        app.run(
            host=os.environ.get("HOST", "localhost"),
            port=os.environ.get("PORT", 8000),
        )
    else:
        app.run(
            use_reloader=True,
            host=os.environ.get("HOST", "localhost"),
            port=os.environ.get("PORT", 5000),
        )
