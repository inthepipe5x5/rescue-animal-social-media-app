import os
from Project.services.data.gdc_pipeline import GeoDBCitiesPipeline


if __name__ == "__main__":
    GeoDBCitiesPipeline.seed_initial_cities()
