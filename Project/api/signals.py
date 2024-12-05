from blinker import Namespace

# Create a namespace for our custom signals
signals = Namespace()

# Session-based signals
session_reload_required = signals.signal("session-reload-required")
session_location_changed = signals.signal("session-location-changed")
user_animal_preferences_changed = signals.signal("user_animal_preferences_changed")

# Service-based signals
# Petfinder
next_location_required = signals.signal(
    "next-location-required"
)  # use this when PetFinder API cannot locate location
end_of_content = signals.signal(
    "end-of-content"
)  # when fetching api data from a generator has exhausted all possible data

fetch_petfinder_breeds = signals.signal(
    "fetch-petfinder-breeds"
)  # to signal that /breeds data are missing and need to be fetched
fetch_petfinder_types = signals.signal(
    "fetch-petfinder-types"
)  # to signal that /types data are missing and need to be fetched for all animal types
petfinder_breeds_loaded = signals.signal(
    "petfinder-breeds-loaded"
)  # to signal that /breeds data fetched
petfinder_types_loaded = signals.signal(
    "petfinder-types-loaded"
)  # to signal that /types data fetched for all animal types

# GeoDBCities
fetch_city_details = signals.signal("fetch-city-details")

# Pipeline signals
pipeline_created = signals.signal('pipeline-created') #after seed scraping is done
pipeline_required = signals.signal('pipeline-required') #when a pipeline is needed but not created
requesting_pf_animals = signals.signal("requesting-pf-animals") #look in db for animals
requesting_pf_orgs = signals.signal("requesting-pf-orgs") #look in db for orgs
api_data_found_in_db = signals.signal("api-data-found-in-db")
api_data_not_found_in_db = signals.signal("api-data-not-found-in-db")
general_scrape_request_received = signals.signal("general-scrape-request-received")
parse_validate_data = signals.signal("parse-validate-data")
data_saved = signals.signal("data-saved")
continue_scraping = signals.signal("continue-scraping")
