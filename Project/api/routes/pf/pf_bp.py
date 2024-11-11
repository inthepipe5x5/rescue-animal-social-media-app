from flask import Blueprint, request, redirect, url_for, jsonify
from dotenv import load_dotenv
from urllib.parse import urljoin
import requests
from time import sleep
from services import pf as api, geodb
from core import AnimalReqParams, RequestedContent
from schemas import Animal, AnimalListResponseSchema, AnimalSchema
from core import db

pf_bp = Blueprint("pf", __name__, url_prefix="/pf")
load_dotenv()


@pf_bp.route("/animals", methods=["POST"])
def return_animals():
    """Route to return scraped PetFinder /animals data"""

    params = request.body.get("params")


@pf_bp.route("/animals/scrape", methods=["POST"])
def scrape_animals():
    """Route to scrape /animals"""

    params = request.body.get("params")
    AnimalReqParams.loads(params)

    min_params = [
        ("limit", 100),
        ("location", "43.651070,-79.347015"),
        ("request_url", urljoin(api.BASE_API_URL, "animals", params)),
    ]
    # set min params
    if min_params not in params:
        for param in min_params:
            params.setdefault(param[0], param[1])

    response = api._get_animals(params=params)
    if response:
        response.raise_for_status()
        data: RequestedContent = response.json()
        validated_data = Animal(schema=AnimalSchema)
        Animal.db_bulk_insert_mapping(session=db.session)

        next_url = Animal.get_next_url(data.get("pagination", {}))
        params.setdefault("request_url", next_url)
        sleep(20)
        request.post(url_for("scrape_animals", _external=True), params=params)
        return jsonify({"data": validated_data})
