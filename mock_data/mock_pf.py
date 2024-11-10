from flask import Blueprint, request, redirect, url_for
from dotenv import load_dotenv
from urllib.parse import urljoin
from time import sleep
from Project.package.PetFinderAPI import PetFinderAPI
from Project.package.petfinder_types import AnimalReqParams, RequestedContent
from Project.data.__init__ import Animal, AnimalListResponseSchema, AnimalSchema
from Project.db import db

mock_pf_bp = Blueprint("data", __name__, url_prefix="/mock")
load_dotenv()

@mock_pf_bp.route("/animals", methods=["POST"])
def return_animals():
    """Route to return scraped PetFinder /animals data
    """
    
    params = request.body.get("params")
    
    
    
@mock_pf_bp.route("/animals/scrape", methods=["POST"])
def scrape_animals():
    """Route to scrape /animals
    """
    
    params = request.body.get("params")
    min_params = [("limit", 100), ("location", "43.651070,-79.347015"), ('request_url', urljoin(PetFinderAPI.BASE_API_URL,'animals',params))]
    #set min params
    if min_params not in params:
        for param in min_params:
            params.setdefault(param[0], param[1])
    
    response = PetFinderAPI._get_animals(params=params)
    if response:
        response.raise_for_status()
        data: RequestedContent = response.json()
        validated_data = Animal(schema=AnimalSchema)
        Animal.db_bulk_insert_mapping(session=db.session)


        next_url = Animal.get_next_url(data.get('pagination', {}))
        params.setdefault('request_url', next_url)
        sleep(20)
        return redirect(url_for('scrape_animals',params=params))                        
