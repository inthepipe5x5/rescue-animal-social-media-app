import json
import os
import os
import pandas as pd
from typing import List, Callable, Dict, Optional
from sqlalchemy.orm import Session
from Project.utils.filemanager import FileManager
from Project.core.constants import default_session_dict, DEFAULT_LOCATION


class Pipeline(FileManager):
    """
    A modular pipeline class for managing directories, CSVs, DataFrames, and database population.

    Key Features

    Directory Management: Ensures directories exist or creates them.
    CSV Handling: Reads/writes CSV files and transforms them into DataFrames.
    Database Population: Inserts DataFrame rows into a database with optional batch commits.
    Modular Subclassing: Supports specific pipelines by subclassing
    """

    # set starting city
    starting_city = None
    STARTING_CITY_PATH = os.path.join(
        os.getcwd(),
        "mock_data/geodbcities/cities_details/gdc_toronto_details_parsed.json",
    )
    with open(STARTING_CITY_PATH, "r") as default_city_json:
        starting_city = (
            json.loads(default_city_json)
            or default_session_dict.get(DEFAULT_LOCATION)["city"]
        )

    # Constants
    PWD = os.getcwd()

    def __init__(
        self,
        api: object,
        base_path: str,
        db_session: Session,
        csv_headers: Optional[Dict[str, list[str]]],
        hierarchy: List[str] = ["country", "state", "city"],
    ):
        """
        Initialize the pipeline with a base directory path and database session.

        Args:
            base_path (str): Base directory for data.
            db_session (Session): SQLAlchemy session for database operations.
        """
        super().__init__(base_folder=base_path, hierarchy=hierarchy)
        self.base_path = base_path or os.getcwd()
        self.db_session = db_session
        self.CSV_COLUMN_HEADERS = csv_headers if csv_headers else {}
        self.api = api
        
        #set up pipeline -> create directories, CSV files
        self.setup_pipeline(
            directories=self.hierarchy,
            csv_files=hierarchy,
            csv_headers=self.CSV_COLUMN_HEADERS,
        )

    # @staticmethod
    # def ensure_directories_exist(base_path: str, folders: List[str]) -> None:
    #     """
    #     Ensure specified directories exist; create them if they don't.

    #     Args:
    #         base_path (str): The base directory path.
    #         folders (List[str]): List of folder names to ensure/create.
    #     """
    #     for folder in folders:
    #         folder_path = os.path.join(base_path, folder)
    #         if not os.path.exists(folder_path):
    #             os.makedirs(folder_path)
    #             print(f"Created directory: {folder_path}")
    #         else:
    #             print(f"Directory already exists: {folder_path}")

    # @staticmethod
    # def ensure_csv_files_exist(
    #     base_path: str,
    #     folders: List[str],
    #     csv_files: List[str],
    #     csv_headers: Dict[str, List[str]],
    #     write_to_csv_function: Callable[[str, Dict[str, List[str]]], None],
    # ) -> None:
    #     """
    #     Ensure specified CSV files exist; create them with headers if they don't.

    #     Args:
    #         base_path (str): Base directory path.
    #         folders (List[str]): List of folders to check in.
    #         csv_files (List[str]): List of CSV file names to check/create.
    #         csv_headers (Dict[str, List[str]]): Mapping of file names to headers.
    #         write_to_csv_function (Callable): Function to write data to CSV.
    #     """
    #     for folder in folders:
    #         folder_path = os.path.join(base_path, folder)
    #         if not os.path.exists(folder_path):
    #             os.makedirs(folder_path)
    #             print(f"Created directory: {folder_path}")

    #         for csv_file in csv_files:
    #             file_path = os.path.join(folder_path, csv_file)
    #             if not os.path.exists(file_path):
    #                 write_to_csv_function(file_path, csv_headers.get(csv_file, []))
    #                 print(f"Created CSV file with headers: {file_path}")
    #             else:
    #                 print(f"CSV file already exists: {file_path}")

    @staticmethod
    def csv_to_df(csv_name: str, na_values: List[str]) -> pd.DataFrame:
        """
        Read a CSV file into a DataFrame, handling NA values.

        Args:
            csv_name (str): Name of the CSV file.
            na_values (List[str]): List of values to treat as NA.

        Returns:
            pd.DataFrame: The loaded DataFrame.
        """
        return pd.read_csv(csv_name, na_values=na_values).where(pd.notnull, None)

    def df_to_db(
        self, df: pd.DataFrame, model_class: type, commit_interval: int = 100
    ) -> None:
        """
        Populate the database with data from a DataFrame.

        Args:
            df (pd.DataFrame): DataFrame with data to populate the database.
            model_class (type): SQLAlchemy model class for the table.
            commit_interval (int): Number of rows to commit per transaction.
        """
        rows = df.to_dict(orient="records")
        for i, row in enumerate(rows):
            record = model_class(**row)
            self.db_session.add(record)
            if (i + 1) % commit_interval == 0:
                self.db_session.commit()
                print(f"Committed {i + 1} rows.")
        self.db_session.commit()
        print(f"Final commit completed for {len(rows)} rows.")

    def setup_pipeline(
        self,
        directories: List[str],
        csv_files: List[str],
        csv_headers: Dict[str, List[str]],
    ) -> None:
        """
        Set up the pipeline: directory and CSV management, data transformation, and DB population.

        Args:
            directories (List[str]): List of directories to manage.
            csv_files (List[str]): List of CSV files to manage.
            csv_headers (Dict[str, List[str]]): Mapping of CSV file names to headers.
            data_schema(Schema) Marshmallow Schema to validate data.
            model_class (type): SQLAlchemy model class for DB population.
            data_fetcher (str): Str reference of function to fetch or transform data into a DataFrame.
        """
        self.ensure_directories_exist(self.base_path, directories)
        self.ensure_csv_files_exist(
            self.base_path, directories, csv_files, csv_headers, self.write_to_csv
        )

    # def save_data(self, data, data_to_df_converter, *schemas, *models):
    #     data_df = data_to_df_converter
    #     self.df_to_db(data_df, model_class)
    #     print("Pipeline execution completed.")
