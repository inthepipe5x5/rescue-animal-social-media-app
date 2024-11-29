import csv
from pathlib import Path
import shutil
import unittest
import json
import os
import dotenv
from typing import Dict, Any, Callable, List, Union
from flask import Flask
from Project.core.app import create_app
from Project.core.constants import default_session_keys

dotenv.load_dotenv()


class TestCommon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):

        cls.loaded_data = {}

    @property
    def test_data_mapping():
        mapping_dict = {
            "test_user": "test_user.json",
            "test_location": "gdc_toronto_details.json",
            "pf_animal_expected": "pf_animal_parsed.json",
            "pf_org_expected": "pf_org_parsed.json",
            "pf_animal_original": "pf_sample_single_animal.json",
            "pf_org_original": "pf_sample_single_org.json",
            "gdc_cities": "gdc_sample_cities.json",  # main cities route
            "gdc_cities_schema": "gdc_cities_schema.json",
            "gdc_city_details": "gdc_sample_city_details.json",  # main city details route
            "gdc_city_details_schema": "gdc_city_details_schema.json",
            "gdc_country_places_details": "gdc_sample_country_places_details.json",  # do not use
            "gdc_country_places_details_schema": "gdc_country_places_details_schema.json",  # do not use
        }

        return {
            key: os.path.join("/mock_data", value)
            for key, value in mapping_dict.items()
        }

    def setUp(self, *setup_funcs):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Execute additional setup functions
        for setup_func in setup_funcs:
            setup_func(self)

    def tearDown(self, *teardown_funcs):
        self.db.session.remove()
        self.db.drop_all()
        self.app_context.pop()
        self.loaded_data.clear()

        # Execute additional teardown functions
        for teardown_func in teardown_funcs:
            teardown_func(self)

        # remove "CSV" directory

    @classmethod
    def load_setup_file(
        cls, file_name: str, dict_keys: list[str] = None
    ) -> List[str, int, bool, dict]:
        """
        Load a setup file and return its contents as a Python data structure.
        """
        setup_parent_directory = "/mock_data"
        file_path = os.path.join(
            os.getcwd(),
            cls.find_file_relative_path(
                parent_dir=setup_parent_directory, target_file=file_name
            ),
        )

        if file_name.endswith(".csv"):
            with open(file_path, newline="") as csvfile:
                if dict_keys:
                    reader = csv.DictReader(csvfile, fieldnames=dict_keys)
                    return {row[dict_keys[0]]: row for row in reader}
                else:
                    reader = csv.reader(csvfile)
                    return list(reader)

        elif file_name.endswith(".json"):
            with open(file_path, "r") as file:
                return json.load(file)

        else:  # Assume it's a text file
            with open(file_path, "r") as file:
                return file.readlines()

    def get_test_data(self, key: str) -> Dict[str, Any]:
        """
        Get test data for a given key. If not loaded, load it from the corresponding file.
        """
        if key not in self.loaded_data:
            file_name = self.test_data_mapping.get(key)
            if file_name:
                self.loaded_data[key] = self.load_setup_file(file_name=file_name)
            else:
                raise KeyError(f"No test data mapping found for key: {key}")
        return self.loaded_data[key]

    def find_file_relative_path(
        target_file: str, parent_dir: str = "/mock_data"
    ) -> Union[str, None]:
        """
        Recursively search for a target file within a given parent directory
        and return the relative path from the parent to the target file.

        Parameters:
        - parent_dir (str or Path): The parent directory to start the search from.
        - target_file (str): The name of the target file to search for.

        Returns:
        - str: the relative path to the target file if found
        """
        parent_dir = Path(parent_dir)
        for file in parent_dir.rglob(target_file):
            relative_path = file.relative_to(parent_dir)
            return str(relative_path)
        return None


if __name__ == "__main__":
    unittest.main()
