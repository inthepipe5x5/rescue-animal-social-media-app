from flask import (
    g,
    request,
    redirect,
    url_for,
    Blueprint,
    flash,
    render_template,
    session,
    jsonify,
    current_app,
)
from flask_login import login_required, current_user
from dotenv import load_dotenv
from werkzeug.datastructures import MultiDict
from sqlalchemy.exc import IntegrityError  # type: ignore
from Project.core.constants import CURR_ANIMALS_KEY, USER_LOCATION_KEY
from Project.schemas.geography import CitySchema
from Project.models.users import UserTravelPreferences
from Project.core.methods import (
    active_authenticated_user,
    do_logout,
    do_login,
    save_location_to_session,
)
from Project.core.constants import default_session_dict
from Project.core.extensions import db
from Project.core.methods import load_session
from Project.models import User, UserFavorites, UserLocation, UserAnimalPreferences
from Project.services.petfinder.helper import (
    add_location_to_g,
    get_anon_preference,
    update_anon_preferences,
    update_user_preferences,
)
from Project.forms import (
    UserAddForm,
    UserEditForm,
    UserExperiencesForm,
    UserLocationForm,
    AnonExperiencesForm,
    SpecificAnimalPreferencesForm,
    UserTravelForm,
)

load_dotenv()

users_bp = Blueprint(
    "users", __name__, url_prefix="users", url_defaults=url_for("users_bp.profile")
)


##############################################################################
# General user routes:
@login_required
@users_bp.route("/")
def list_users():
    # """Page with listing of users.

    # Can take a 'q' param in querystring to search by that username.
    # """

    # search = request.args.get("q")

    # if not search:
    #     users = User.query.all()
    # else:
    #     users = User.query.filter(User.username.like(f"%{search}%")).all()

    # return render_template("index.html", users=users)
    with current_app.app_context():
        return redirect(url_for("users_bp.profile"))


@users_bp.route("/<int:user_id>")
def show_user(user_id):
    user = User.query.get_or_404(user_id)
    user_location_form = UserLocationForm(obj=user.location)
    user_travel_form = UserTravelForm(obj=user.travel_preference)
    return render_template(
        "show.html",
        user=user,
        user_location_form=user_location_form,
        user_travel_form=user_travel_form,
    )


# Form route available to both anon and users but only user location is saved to db
@users_bp.route("/location", methods=["GET", "POST"])
def user_location_form():
    users_bp.logger.info(
        f"Request method: {request.method}, Current user.location: {current_user.location if (active_authenticated_user() and current_user.location) else 'No Saved Location'}"
    )
    try:
        if active_authenticated_user() and current_user.location:
            form = UserLocationForm(obj=current_user.location)
        else:
            form = UserLocationForm()

        if form.validate_on_submit():
            if current_user.location:
                location = current_user.location
                form.populate_obj(location)
                users_bp.logger.info("Updating existing location")
            else:
                location = UserLocation(user_id=current_user.id)
                form.populate_obj(location)
                users_bp.logger.info("Creating new location")

            if form.geolocation.data:
                coordinates = form.geolocation.data
                location.geolocation = CitySchema.format_geolocation(coordinates)
                users_bp.logger.info(f"Setting geolocation: {location.geolocation}")

            location.city = location.city.lower() if location.city else None

            db.session.add(location)
            db.session.commit()

            users_bp.logger.info(f"Location saved: {form.data}")
            flash("Location updated successfully!", "success")

            # update session logic
            location_dict = save_location_to_session(location_dict=location.serialize())
            if request.is_json:
                return jsonify({"location": location_dict})

            viewed_content = session.get("VIEWED_CONTENT_LIST", [])
            # load session
            load_session()
            # keep viewed content in session
            session["VIEWED_CONTENT_LIST"] = viewed_content

            return redirect(url_for("show_user", user_id=current_user.id))

        return render_template(
            "/form.html",
            form=form,
            form_title="Where are you located?",
            page_scripts=[
                url_for("static", filename="geolocation.js"),
                url_for("static", filename="setStateCountryInput.js"),
            ],
        )
    except Exception as e:
        users_bp.logger.error(f"Error in user_location_form: {str(e)}")
        db.session.rollback()
        flash(
            "An error occurred while updating your location. Please try again.", "error"
        )


@users_bp.route("/location/update", methods=["POST"])
def update_location():
    """Route to set location for search results

    Returns:
        _type_: _description_
    """
    from Project.core.types import UserLocationData

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
    current_app.session[USER_LOCATION_KEY] = location

    success_msg = f"App.py: Current CURR_LOCATION set to: {session['CURR_LOCATION']}"
    add_location_to_g(session=session, g=g)

    return jsonify({"message": success_msg})


@login_required
@users_bp.route("/travel", methods=["GET", "POST"])
def user_travel_preferences():
    travel_preferences = UserTravelPreferences.query.filter_by(
        user_id=current_user.id
    ).first()

    if not current_user.location:
        flash("Please set your location details first", "warning")
        return redirect(url_for("user_location_form"))

    if travel_preferences:
        form = UserTravelForm(obj=travel_preferences)
    else:
        form = UserTravelForm()

    if form.validate_on_submit():
        if not travel_preferences:
            travel_preferences = UserTravelPreferences(user_id=current_user.id)
        # update the sqlalchemy object
        form.populate_obj(travel_preferences)

        # save to db
        db.session.add(travel_preferences)
        db.session.commit()

        # update distance_pref stored in session
        session.modified = True
        new_distance_pref = form.data.get("distance_filter_preference", 100)
        session["DISTANCE_PREF"] = new_distance_pref

        # flash message to user for feedback
        flash("Travel preferences updated successfully!", "success")
        return redirect(url_for("show_user", user_id=current_user.id))

    return render_template(
        "/form.html",
        form=form,
        form_title="How far are you willing to travel?",
        page_scripts=[url_for("static", filename="setTravelPreference.js")],
    )


@login_required
@users_bp.route("/favorite/<fav_type>", methods=["GET"])
def show_user_favorites(fav_type):
    """Add or toggle a favorite for the currently-logged-in user."""

    fav_type = "all" if not fav_type else fav_type.lower()

    user = (
        current_user
        if current_user.is_authenticated
        else session.get("CURR_USER", None)
    )
    if not user:
        flash("Access unauthorized.", "danger")
        return redirect(url_for("login"))

    try:
        if fav_type == "all":
            user_favorites = UserFavorites.get_favorites(user_id=user.id)

        # return fave orgs
        elif fav_type.lower() in (
            "orgs",
            "organizations",
            "organization",
            "rescue",
            "rescues",
        ):
            user_favorites = UserFavorites.get_orgs_favorites(user_id=user.id)

        # return fave animals if fave_type not specified
        # elif fav_type == 'animals':
        else:
            user_favorites = UserFavorites.get_animal_favorites(user_id=user.id)

        return jsonify(
            {
                "user_id": user.id,
                "action": fav_type,
                "results": user_favorites if user_favorites else [],
            }
        )

    except Exception as e:
        # db.session.rollback()
        return (
            jsonify(
                {
                    "error": "Error getting favorites @ show_user_favorites API route =>"
                    + str(e)
                }
            ),
            500,
        )


@login_required
@users_bp.route("/favorite/<int:favorite_id>", methods=["POST"])
def user_favorite(favorite_id):
    """Add or toggle a favorite for the currently-logged-in user."""

    is_animal = request.args.get("is_animal", "true").lower() == "true"
    action = request.args.get("action", "toggle").lower()

    user = (
        current_user
        if current_user.is_authenticated
        else session.get("CURR_USER", None)
    )
    if not user:
        flash("Access unauthorized.", "danger")
        return redirect(url_for("login"))

    try:
        if action == "add":
            user.add_favorite(favorite_id=favorite_id, is_animal=is_animal)
            message = f"Added {'Animal' if is_animal else 'Rescue Org'} #{favorite_id} to favorites"
        elif action == "toggle":
            result = user.toggle_favorite(favorite_id=favorite_id, is_animal=is_animal)
            message = f"{'Added' if result else 'Removed'} {'Animal' if is_animal else 'Rescue Org'} #{favorite_id} {'to' if result else 'from'} favorites"
        else:
            return jsonify({"error": "Invalid action"}), 400

        flash(message)
        return jsonify(
            {
                "favorite_id": favorite_id,
                "action": action,
                "result": result if action == "toggle" else True,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/animal_types", methods=["GET", "POST"])
def update_animal_types():
    if request.method == "POST":
        selected_types = request.form.getlist("animal_types")
        # Update the current user's animal types via the current_user proxy
        if active_authenticated_user():
            # Update the current user's animal types
            current_user.animal_types = selected_types
            try:
                db.session.commit()
                flash("Animal types updated successfully", "success")
            except Exception as e:
                db.session.rollback()
                flash("An error occurred while updating animal types", "error")
                users_bp.logger.error(
                    f"Error updating animal_types for user {current_user.id} @ {request.url} => {str(e)}"
                )
                return (
                    jsonify({"error": "An error occurred while updating animal types"}),
                    500,
                )
        else:
            # Limit anonymous users to just one selection
            selected_type = selected_types[0] if selected_types else "dog"
            session["ANIMAL_TYPES"] = [selected_type]
            flash("Animal type updated successfully", "success")

        return jsonify({"animal_types": current_user.animal_types}), 201

    # handle get requests
    else:
        animal_types = (
            current_user.animal_types
            if active_authenticated_user()
            else default_session_dict.get(CURR_ANIMALS_KEY, ["dog"])
        )
        return jsonify({"animal_types": animal_types}), 200


@login_required
@users_bp.route("/preferences/<animal_type>", methods=["GET", "POST"])
def animal_preferences(animal_type):
    if request.method == "GET":
        user_animal_prefs = UserAnimalPreferences.get_user_animal_pref_obj(
            u_id=current_user.id, animal_type=animal_type
        )

    if request.method == "POST":
        # list of SpecificAnimalPreferences field names
        form_field_names = [
            "user_id",
            "species",
            "declawed",
            "shots_current",
            "special_needs",
            "spayed_neutered",
            "house_trained",
            "child_friendly",
            "dogs_friendly",
            "cats_friendly",
            "breeds",
            "color",
            "coat",
            "age",
            "personality_tags",
            "size",
            "gender",
        ]
        # create data obj from request.form to be passed into the  WTForms class
        submitted_data = {
            key: request.form[key] for key in request.form if key in form_field_names
        }
        # create a new flask WTForms instance to prevent submitted form data from being overridden by user_animal_prefs
        form = SpecificAnimalPreferencesForm(animal_type, obj=submitted_data)
    else:
        if "user_id" in user_animal_prefs:
            del user_animal_prefs["user_id"]
        if "species" in user_animal_prefs:
            del user_animal_prefs["species"]
        form = SpecificAnimalPreferencesForm(animal_type, MultiDict(user_animal_prefs))

    if form.validate_on_submit():
        try:
            new_prefs = UserAnimalPreferences.update_user_pref(
                user_id=current_user.id,
                species=animal_type,
                form_data_obj=form.data,
            )
            print(new_prefs)
            # reset current_animal_page count to 1
            session.pop("CURRENT_DISCOVER_ANIMALS_PAGE", 1)

            flash(f"Successfully updated {animal_type} preferences.", "success")
            # return redirect(url_for("animal_pref_data", animal_type=animal_type))
            return redirect(url_for("show_user", user_id=current_user.id))
        except Exception as e:
            users_bp.logger.error(f"Error updating preferences: {e}")
            db.session.rollback()
            flash(
                "An error occurred while saving your preferences. Please try again.",
                "danger",
            )
            return redirect(url_for("users_bp.profile"))

    return render_template(
        url_for("templates", "users/user_animal_preferences.html"),
        form=form,
        endpoint_param=animal_type,
    )


@login_required
@users_bp.route("/profile", methods=["GET", "POST"])
def profile():
    """Update profile for current user."""
    # TODO write this to accept a dict of values to update on the current user
    if request.method == "POST" and request.body:
        pass

    if not active_authenticated_user():
        flash("Access unauthorized.", "danger")
        return redirect(url_for("login"))

    else:
        active_user = current_user._get_current_object()
        form = UserEditForm(obj=active_user)

        if form.validate_on_submit():
            if User.authenticate(form.username.data, form.password.data):
                form.populate_obj(active_user)
                db.session.add(active_user)
                db.session.commit()  # commit to db
                flash("Changes saved successfully", "success")  # show success to user
                return redirect(url_for("show_user", user_id=g.user.id))
            else:
                db.session.rollback()
                flash(
                    "You were unsuccessful, try again", "error"
                )  # show success to user
                return render_template("edit.html", form=form, user=active_user)

        return render_template("edit.html", form=form, user=active_user)


@users_bp.route("/delete", methods=["POST"])
def delete_user():
    """Delete user."""

    if not active_authenticated_user() or "CURR_USER" not in session:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(session["CURR_USER"])
    db.session.commit()
    flash("Deleted current user successfully", "success")
    return redirect("/signup")


##############################################################################
@users_bp.route("/signup", methods=["GET"])
def signup():
    """Route to redirect any signup links that need to be updated
    TO BE REMOVED BEFORE PRODUCTION

    Returns:
        redirect to signup_user Flask Route.
    """
    return redirect(url_for("signup_user"))


@users_bp.route("/signup/user", methods=["GET", "POST"])
def signup_user():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    # instantiate add user form
    form = UserAddForm()
    if form.validate_on_submit():
        data = {field.name: field.data for field in form}
        try:

            user = User.signup(**data)
            # save user location
            user_location = UserLocation(
                user_id=user.id, country=form.country.data, state=form.state.data
            )
            # link user_location to user
            user.location = user_location

            # save new user & location to db
            db.session.add(user)
            db.session.add(user_location)
            db.session.commit()

            # seed animal_preferences for the user
            UserAnimalPreferences.seed_user_pref(user_id=user.id)

            # init_orgs =PetFinderAPI.get_orgs_df()
        except IntegrityError:
            flash("Username already taken", "danger")
            db.session.rollback()
            return render_template("signup.html", form=form)

        do_login(user)
        flash("User # {user.id} created successfully: {user.username}", "success")
        # Redirect to location form for additional information
        flash(
            "Please consider enabling geolocation in the browser to help us return more accurate results relative to your location",
            "warning",
        )
        return redirect(url_for("user_location_form"))

    else:

        db.session.rollback()
        return render_template(
            "signup.html",
            form=form,
            page_scripts=[
                url_for("static", filename="geolocation.js"),
                url_for("static", filename="setStateCountryInput.js"),
            ],
            next=True,
        )


@users_bp.route("/signup/preferences", methods=["GET", "POST"])
def signup_preferences():
    """Route to return form for user location (state + country), animal_types

    Returns:
        _type_: _description_
    """
    u_pref_form = UserExperiencesForm()

    if u_pref_form.validate_on_submit():
        # Process u_pref_form submission

        # save form data to g, flask sessions and database
        update_user_preferences(
            form=u_pref_form, session=session, user=session["CURR_USER"]
        )  # pass in a current user

    return render_template("form.html", form=u_pref_form, next=False)


@users_bp.route("/update/types", methods=["GET", "POST"])
def update_animal_types():
    """Route to set the global options for country of origin and animal types

    If GET -> return form page
    If POST -> set 'country' and/or 'animal_types' in sessions

    """
    # handle if POST request with updated data
    if (
        request.args
        and ("animal_types", "ANIMAL_TYPES", "types", "TYPES") in request.body
    ):
        pass
        # TODO: write this wrote to accept API requests from front end

        user = (
            current_user._get_current_object()
            if active_authenticated_user()
            else User()
        )
    else:
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
