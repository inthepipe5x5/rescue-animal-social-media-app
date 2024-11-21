import os
import glob
from csv import DictWriter
from typing import Any, Dict, List

from marshmallow import ValidationError
from pandas import pandas as pd
from psycopg2 import IntegrityError
from pycountry import countries, subdivisions
from sqlalchemy import func

from Project.core import db
from Project.services import geodb
from Project.models import City, CitySchema
from canada_us_states_cities import usa, canada

# get present working directory
PWD = os.path.abspath(__file__)
# list to represent country/state/cities relationship => use in deserializing & creating folders/CSVs
country_state_cities = ["country", "states", "cities"]

# Update Canadian provinces and territories
canada_updated = {
    country_state_cities[0]: "Canada",
    country_state_cities[1]: {
        province: {country_state_cities[2]: cities}
        for province, cities in canada.items()
    },
}

# Update USA states
usa_updated = {
    country_state_cities[0]: "United States of America",
    country_state_cities[1]: {
        province: {country_state_cities[2]: cities} for province, cities in usa.items()
    },
}
# CSV column headers matching City db.Model attributes
CSV_COLUMN_HEADERS = [
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
CSV_NEWLINE = ","


def country_state_dict_to_csv(data: dict, filename: str):
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
    if "_cities.csv" not in filename:
        filename = filename.replace(" ", "_") + "_cities.csv"

    with open(filename, "w", newline="") as csvfile:
        writer = DictWriter(csvfile, fieldnames=CSV_COLUMN_HEADERS)
        writer.writeheader()

        country_name = data["country"]
        country = countries.search_fuzzy(country_name)[0]
        country_code = country.alpha_2

        for state, state_data in data["states"].items():
            try:
                subdivision = subdivisions.search_fuzzy(f"{state}, {country_name}")[0]
                region_code = subdivision.code.split("-")[1]
            except LookupError:
                region_code = CSV_NEWLINE  # If state/region code is not found

            for city in state_data["cities"]:
                writer.writerow(
                    [
                        "CITY",  # type
                        city,  # name
                        country_name,
                        country_code,
                        state,
                        region_code,
                        CSV_NEWLINE,  # geolocation (to be filled by API)
                        CSV_NEWLINE,  # population (to be filled by API)
                        CSV_NEWLINE,  # postal_code (to be filled by API)
                    ]
                )


def ensure_directories_exist(base_path: str, folders: List[str]) -> None:
    """
    Check if specified folders exist and create them if they don't.

    Args:
        base_path (str): The base directory path.
        folders (List[str]): List of folder names to check/create.
    """
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Created directory: {folder_path}")
        else:
            print(f"Directory already exists: {folder_path}")


def ensure_csv_files_exist(
    base_path: str, folders: List[str], csv_files: List[str], csv_data: dict
) -> None:
    """
    Check if specified CSV files exist in each folder and create them if they don't.
    The created CSV files will include the necessary column headers.

    Args:
        base_path (str): The base directory path.
        folders (List[str]): List of folder names to check in.
        csv_files (List[str]): List of CSV file names to check/create.
    """
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Created directory: {folder_path}")

        for csv_file in csv_files:
            file_path = os.path.join(folder_path, csv_file)
            if not os.path.exists(file_path):
                country_state_dict_to_csv(filename=csv_file, data=csv_data)
                print(f"Created CSV file with headers: {file_path}")
            else:
                print(f"CSV file already exists: {file_path}")


def country_cities_csv_to_df(
    csv_name: str = "canada_cities.csv", na_values: list = [""]
) -> None:
    # Read the CSV file
    df = pd.read_csv(csv_name, na_values=na_values)
    df = df.where(pd.notnull(df), None)
    return df


def populate_db_from_csv(csv_folder):
    csv_files = glob.glob(os.path.join(csv_folder, "*.csv"))

    for csv_file in csv_files:
        print(f"\nProcessing {os.path.basename(csv_file)}:")
        # convert csv -> df
        df = country_cities_csv_to_df(csv_file)
        # convert df  -> db entries
        populate_db_from_df(df)


def create_country_csvs(*country_data: Dict[str, Any]) -> str:
    """
    Create CSV files for an arbitrary number of countries.

    :param country_data: Variable number of dictionaries containing country data.
                         Each dictionary should have the format: {'country_name': data_dict}
    :return: Path to the CSV folder
    """
    csv_folder = ensure_directories_exist(base_path=PWD, folders=["csv"])

    for country_dict in country_data:
        for country_name, data in country_dict.items():
            filename = f"{country_name.lower().replace(' ', '_')}_cities.csv"
            filepath = os.path.join(csv_folder, filename)
            country_state_dict_to_csv(data=data, filename=filepath)
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

    # Build the query
    query = City.query

    if city:
        query = query.filter(func.lower(City.name) == func.lower(city))
    if state:
        query = query.filter(func.lower(City.region_code) == func.lower(state))
    if country:
        query = query.filter(func.lower(City.country_code) == func.lower(country))

    # Execute the query
    results = query.all()

    return results if results else []
