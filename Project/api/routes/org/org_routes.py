from flask import (
    request,
    redirect,
    url_for,
    Blueprint,
    flash,
    render_template,
    session,
    jsonify,
)
from dotenv import load_dotenv
import os

from core import (
    login_required,
    db,
    current_user,
    active_authenticated_user,
    do_logout,
    do_login,
)
from models import User, UserFavorites, UserLocation, UserAnimalPreferences
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

load_dotenv()

orgs_bp = Blueprint("orgs", __name__, url_prefix="orgs")


@orgs_bp.route("/discover/orgs", methods=["GET", "POST"])
def discover_orgs():
    # grab current page_count in session
    current_page_count = session.get("CURRENT_DISCOVER_ORGS_PAGE", 1)
    if request.method.upper() == "GET":
        # direct to current page count
        return redirect(url_for("discover_orgs_page", page=current_page_count))

@orgs_bp.route("/discover/orgs/<int:page>", methods=["GET"])
def discover_orgs_page(page):
    # args = request.args if request.args else {}

    # # handle no page
    # if not page:
    #     page = session.get("CURRENT_DISCOVER_ORGS_PAGE", 1)
    #     if args and "next" in args:
    #         # increment page
    #         page = page + 1
    #         # update session
    #         session["CURRENT_DISCOVER_ORGS_PAGE"] = page
    #     if args and "prev" in args:
    #         # increment page
    #         page = page - 1
    #         # update session
    #         session["CURRENT_DISCOVER_ORGS_PAGE"] = page
    # # handle invalid page attempts & or if the user hasn't visited page 1 yet
    # if not "ANIMAL_RESULTS_DICT" in session:
    #     flash("Sorry, we haven't found that many friends to adopt yet!")
    #     # make post request to seed
    #     requests.post(url_for("discover_orgs"))
    #     sleep(3)
    #     redirect(url_for("discover_orgs_page", page=page))

    # animal_id_list = session.get("ANIMAL_RESULTS_DICT").get(page, [])

    # animals = petpy.animals(animal_id=animal_id_list)

    # return render_template("animalResults.html", animals=animals)

    return jsonify({"THIS IS UNDER DEVELOPMENT"})

