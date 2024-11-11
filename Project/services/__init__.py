from .petfinder import PetFinderAPI
from .geography import geodb_api

# initialize services here
pf = PetFinderAPI()
geodb = geodb_api()

# This allows: from Project.services import pf, geodb

if __name__ == "__main__":
    # pf = PetFinderAPI()
    # geodb = geodb_api()

    pass
