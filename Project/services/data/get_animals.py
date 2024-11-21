from sqlalchemy import desc, func
from Project.core import db
from Project.services import pf, geodb
from Project.core.constants import default_session_keys, DEFAULT_LOCATION
from Project.models import Animal, AnimalCity, City

starting_city = default_session_keys.get(DEFAULT_LOCATION)["city"]

if __name__ == "__main__":
    try:
        all_cities_by_population = (
            db.session.query(City).order_by(desc(City.population)).all()
        )

        for city in all_cities_by_population:
            if city.name.casefold != starting_city.casefold:
                geolocation = (
                    city.geolocation
                    if "geolocation" in city
                    else f"{city.name},{city.region_code}"
                )
                params = {
                    "location": geolocation,
                    "limit": 100,
                    "sort": "distance",
                    "distance": 500,
                }
                animals = pf._get_request(endpoint="animals", params=params)
                if animals.status_code == 200:
                    AnimalCity.create_from_combined_dict
    
    
    except Exception as e:
        print(e)
