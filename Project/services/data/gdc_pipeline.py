import os
import glob
from csv import DictWriter
from pathlib import Path
from typing import Any, Dict, List

from marshmallow import ValidationError
from pandas import pandas as pd
from psycopg2 import IntegrityError
from pycountry import countries, subdivisions
from sqlalchemy import func
from sqlalchemy.orm import Session

from Project.core import db
from Project.core.constants import default_session_dict, LOCATION_SESSION_KEY
from Project.services import geodb
from Project.models import City, CitySchema
from canada_us_states_cities import usa, canada

from Project.services.data.pipeline import Pipeline


class GeoDBCitiesPipeline(Pipeline):

    # get present working directory

    PWD = Path(os.path.abspath(os.path.dirname(__file__)))

    # list to represent country/state/cities relationship => use in deserializing & creating folders/CSVs
    COUNTRY_STATE_CITIES = ("country", "states", "cities")

    # CSV column headers matching City db.Model attributes
    CITY_CSV_COLUMN_HEADERS = [
        "type",
        "name",
        "country",
        "country_code",
        "state",
        "region_code",
        "geolocation",
        "population",
        "postal_code",
    ]

    def __init__(self, base_path: str, db_session: Session):
        super().__init__(base_path, db_session)()

        # Update Canadian provinces and territories
        self.canada_updated = {
            self.COUNTRY_STATE_CITIES[0]: "Canada",
            self.COUNTRY_STATE_CITIES[1]: {
                province: {self.COUNTRY_STATE_CITIES[2]: cities}
                for province, cities in canada.items()
            },
        }

        # Update USA states
        self.usa_updated = {
            self.COUNTRY_STATE_CITIES[0]: "United States of America",
            self.COUNTRY_STATE_CITIES[1]: {
                province: {self.COUNTRY_STATE_CITIES[2]: cities}
                for province, cities in usa.items()
            },
        }

    def country_state_dict_to_csv(self, data: dict, filename: str, newline: str):
        """
        The function `country_state_dict_to_csv` converts a dictionary containing country and state data
        into a CSV file with specific column headers.

        :param data: The `data` parameter is a dictionary containing information about countries and their
        states. It has the following structure:
        :type data: dict
        :param filename: The `filename` parameter in the `country_state_dict_to_csv` function is a string
        that represents the name of the CSV file where the data will be written. It should include the file
        extension (e.g., "output.csv") and specify the path if the file is not in the current working
        """
        newline = newline if newline else self.CSV_NEWLINE

        if "_cities.csv" not in filename:
            filename = filename.replace(" ", "_") + "_cities.csv"

        country_name = data.get("country") or data.get("country_code")

        with open(filename, "w", newline=newline) as csvfile:
            writer = DictWriter(csvfile, fieldnames=self.CITY_CSV_COLUMN_HEADERS)
            writer.writeheader()

            country = countries.search_fuzzy(country_name)[0]
            country_code = country.alpha_2

            for state, state_data in data["states"].items():
                try:
                    subdivision = subdivisions.search_fuzzy(f"{state}, {country_name}")[
                        0
                    ]
                    region_code = subdivision.code.split("-")[1]
                except LookupError:
                    region_code = self.CSV_NEWLINE  # If state/region code is not found

                for city in state_data["cities"]:
                    writer.writerow(
                        [
                            "CITY",  # type
                            city,  # name
                            country_name,
                            country_code,
                            state,
                            region_code,
                            self.CSV_NEWLINE,  # geolocation (to be filled by API)
                            self.CSV_NEWLINE,  # population (to be filled by API)
                            self.CSV_NEWLINE,  # postal_code (to be filled by API)
                        ]
                    )

    def populate_db_from_csv(self, csv_folder):
        csv_files = glob.glob(os.path.join(csv_folder, "*.csv"))

        for csv_file in csv_files:
            print(f"\nProcessing {os.path.basename(csv_file)}:")
            # convert csv -> df
            df = self.csv_to_df(csv_file)
            # convert df  -> db entries
            self.populate_db_from_df(df)

    def create_country_csvs(self, *country_data: Dict[str, Any]) -> str:
        """
        Create CSV files for an arbitrary number of countries.

        :param country_data: Variable number of dictionaries containing country data.
                            Each dictionary should have the format: {'country_name': data_dict}
        :return: Path to the CSV folder
        """
        csv_folder = self.ensure_directories_exist(base_path=self.PWD, folders=["csv"])

        for country_dict in country_data:
            for country_name, data in country_dict.items():
                filename = f"{country_name.lower().replace(' ', '_')}_cities.csv"
                filepath = os.path.join(csv_folder, filename)
                self.country_state_dict_to_csv(data=data, filename=filepath)
                print(f"Created CSV for {country_name}: {filepath}")

        return csv_folder

    def populate_db_from_df(cities_df):
        """
        Populate the database with city data from a DataFrame.

        This function processes a DataFrame of city information, fetches additional
        details from an external API, and updates or adds cities to the database.

        Args:
        cities_df (pd.DataFrame): DataFrame containing city information.

        Returns:
        None
        """

        # Convert DataFrame to a list of dictionaries for bulk processing
        cities_list = cities_df.to_dict("records")

        # Fetch existing cities from the database in bulk
        existing_cities = {
            (city.name, city.state, city.country): city for city in City.query.all()
        }

        # Prepare lists for bulk insert and update
        cities_to_add = []
        cities_to_update = []

        for city_data in cities_list:
            try:
                # Fetch additional data from API
                api_data = geodb.get_city_details(
                    city_data["name"], city_data["country_code"]
                )
                if not api_data:
                    print(
                        f"Could not fetch data for {city_data['name']}. Using available data."
                    )
                    api_data = city_data

                # Process and validate city data
                processed_data = geodb.process_city_data(api_data, city_data["state"])

                # Fill in missing data with API call results
                for field in ["geolocation", "name", "country", "country_code"]:
                    if not processed_data.get(field):
                        print(
                            f"Missing {field} for {city_data['name']}. Attempting to fetch from API."
                        )
                        updated_data = geodb.get_city_details(
                            city_data["name"], city_data["country_code"]
                        )
                        if updated_data and updated_data.get(field):
                            processed_data[field] = updated_data[field]
                        else:
                            print(
                                f"Could not fetch {field} for {city_data['name']} from API."
                            )

                validated_data = CitySchema().load(processed_data)

                # Check if city already exists
                existing_city = City.check_city_exists(
                    city_name=city_data["name"],
                    state=city_data["state"],
                    country=city_data["country"],
                )

                if existing_city:
                    # Update existing city
                    for key, value in validated_data.items():
                        setattr(existing_city, key, value)
                    cities_to_update.append(existing_city)
                    print(f"Updated {existing_city.name} in the database.")
                else:
                    # Add new city
                    new_city = City(**validated_data)
                    cities_to_add.append(new_city)
                    print(f"Added {new_city.name} to the database.")

            except ValidationError as e:
                print(f"Validation error for {city_data['name']}: {e.messages}")
            except Exception as e:
                print(f"Unexpected error for {city_data['name']}: {str(e)}")

        # Bulk insert new cities
        if cities_to_add:
            db.session.bulk_save_objects(cities_to_add)

        # Commit all changes
        try:
            db.session.commit()
            print(
                f"Successfully added {len(cities_to_add)} new cities and updated {len(cities_to_update)} existing cities."
            )
        except IntegrityError as e:
            print(f"Integrity error during bulk operation: {str(e)}")
            db.session.rollback()
        except Exception as e:
            print(f"Unexpected error during bulk operation: {str(e)}")
            db.session.rollback()

    def check_db(location_dict: dict) -> List[object]:
        # return a list of all cities that match the provided criteria, or None if no matches are found.
        city = location_dict.get("city")
        state = location_dict.get("state")
        country = location_dict.get("country")

        # Convert country to alpha_2 if it's a full name
        if country and len(country) > 2:
            try:
                country = countries.search_fuzzy(country)[0].alpha_2
            except LookupError:
                country = None

        # Convert state to alpha_2 if it's a full name
        if state and len(state) > 2:
            try:
                state = subdivisions.search_fuzzy(state)[0].alpha_2
            except LookupError:
                state = None

        # Build the query
        results = City.find(
            city_name=city, state_code=state, country_code=country, return_all=True
        )

        return results if results else []

    def seed_initial_cities(self):
        # create csv folder
        csv_folder = self.ensure_directories_exist(base_path=self.PWD, folders=list("csv"))
        # create country csvs
        csv_folder = self.create_country_csvs(
            {"Canada": self.canada_updated},
            {"United States of America": self.usa_updated},
        )
        self.populate_db_from_csv(csv_folder)


if __name__ == "__main__":
    pass
    """
    1. Input Preparation

    Use canada_updated and usa_updated to structure the nested country-state-city relationships.
    Transform this structure into CSV files with country_state_dict_to_csv() for persistent storage.
    
    2. CSV File Generation

    Call create_country_csvs(canada_updated, usa_updated) to create CSVs in the csv folder. This ensures you have clean, consistent, and formatted data for further processing.
    Pandas DataFrame for Processing

    Use country_cities_csv_to_df() to convert generated CSV files into DataFrames.
    This allows easy manipulation, filtering, and sorting before populating the database.
    Scraping and Data Augmentation

    For each DataFrame, invoke populate_db_from_df().
    Fetch missing data such as geolocation, population, or postal codes using geodb.get_city_details() and ensure API responses align with the schema using geodb.process_city_data().
    Validation and Population

    Validate the processed data with CitySchema().
    Insert or update records in the database:
    New Cities: Add to the cities_to_add list and bulk save.
    Existing Cities: Use City.check_city_exists() to identify matches and update their attributes.
    Commit Changes

    Commit all changes with proper error handling to ensure integrity and avoid transaction rollbacks unless necessary.
    Verification

    Use check_db() to query and verify city entries, ensuring they meet criteria like city name, state, and country.
    
    """
