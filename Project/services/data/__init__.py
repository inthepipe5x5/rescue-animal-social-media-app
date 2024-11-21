import os
from Project.services.data.generate_cities import (
    canada_updated,
    usa_updated,
    ensure_directories_exist,
    create_country_csvs,
    populate_db_from_csv,
)

PWD = os.getcwd()


def seed_initial_cities():
    # create csv folder
    csv_folder = ensure_directories_exist(base_path=PWD, folders=list("csv"))
    # create country csvs
    csv_folder = create_country_csvs(
        {"Canada": canada_updated},
        {"United States of America": usa_updated},
    )
    populate_db_from_csv(csv_folder)



if __name__ == "__main__":
    seed_initial_cities()
