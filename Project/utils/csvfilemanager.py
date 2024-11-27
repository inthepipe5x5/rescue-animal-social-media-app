import os
import csv
from typing import Callable, Dict, List, Optional


class CSVFileManager:
    """
    Python class with functions to manage CSV files in a nested folder structure based on a given hierarchy
    """

    CSV_NEWLINE = ","
    NA_VALUES = ["", "null", "NULL", "none"]

    def __init__(self, base_folder: str = "csv", hierarchy: List[str] = None):
        self.base_folder = os.path.join(os.getcwd(), base_folder)
        self.hierarchy = hierarchy or ["country", "state", "city"]

    @staticmethod
    def ensure_csv_files_exist(
        base_path: str,
        folders: List[str],
        csv_files: List[str],
        csv_headers: Dict[str, List[str]],
        write_to_csv_function: Callable[[str, Dict[str, List[str]]], None],
        data: Optional[dict[str, any]],
    ) -> None:
        """
        Ensure specified CSV files exist; create them with headers if they don't.

        Args:
            base_path (str): Base directory path.
            folders (List[str]): List of folders to check in.
            csv_files (List[str]): List of CSV file names to check/create.
            csv_headers (Dict[str, List[str]]): Mapping of file names to headers.
            write_to_csv_function (Callable): Function to write data to CSV.
        """
        write_to_csv_function = (
            write_to_csv_function
            if write_to_csv_function
            else CSVFileManager.write_to_csv
        )
        for folder in folders:
            folder_path = os.path.join(base_path, folder)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                print(f"Created directory: {folder_path}")

            for csv_file in csv_files:
                file_path = os.path.join(folder_path, csv_file)
                if not os.path.exists(file_path):
                    write_to_csv_function(file_path, csv_headers.get(csv_file, data))
                    print(f"Created CSV file with headers: {file_path}")
                else:
                    print(f"CSV file already exists: {file_path}")

    @staticmethod
    def ensure_directories_exist(base_path: str, folders: List[str]) -> None:
        """
        Ensure specified directories exist; create them if they don't.

        Args:
            base_path (str): The base directory path.
            folders (List[str]): List of folder names to ensure/create.
        """
        for folder in folders:
            folder_path = os.path.join(base_path, folder)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                print(f"Created directory: {folder_path}")
            else:
                print(f"Directory already exists: {folder_path}")

    @staticmethod
    def write_to_csv(file_path: str, headers: List[str], data: dict[str, any]) -> None:
        """
        Write a CSV file with specified headers.

        Args:
            file_path (str): Path to the CSV file.
            headers (List[str]): Column headers for the CSV.
            data()
        """
        with open(file_path, "w", newline=CSVFileManager.CSV_NEWLINE) as csvfile:
            writer = csv.writer(csvfile)
            if headers:
                writer.writerow(headers)
            writer.writerows(data)
            print(f"CSV file created with headers: {file_path}")

        return file_path

    def create_nested_folders(self, dir_hierarchy: List[str]) -> str:
        """
        Create nested folders based on the hierarchy and given values.

        Args:
            dir_hierarchy (List[str]): List of dir_hierarchy corresponding to the hierarchy levels.
            dir_hierarchy: list of
        Returns:
            str: Path to the deepest created folder.
        """
        dir_hierarchy = dir_hierarchy if dir_hierarchy else self.hierarchy

        current_path = self.base_folder
        for path in dir_hierarchy:
            current_path = os.path.join(current_path, path)
            os.makedirs(current_path, exist_ok=True)

        return current_path

    def generate_csv_name(self, values: List[str]) -> str:
        """
        Generate a CSV filename based on the hierarchy and given values.

        Args:
            values (List[str]): List of values corresponding to the hierarchy levels.

        Returns:
            str: Generated CSV filename.
        """
        if len(values) != len(self.hierarchy):
            raise ValueError("Number of values must match the hierarchy levels.")

        return "_".join(values) + ".csv"

    def create_nested_csv_file(
        self, values: List[str], data: List[List], headers: Optional[List[str]] = None
    ) -> str:
        """
        Create a CSV file in the appropriate nested folder structure.

        Args:
            values (List[str]): List of values corresponding to the hierarchy levels.
            data (List[List]): Data to be written to the CSV file.
            headers (Optional[List[str]]): List of column headers for the CSV file.

        Returns:
            str: Full path to the created CSV file.
        """
        folder_path = self.create_nested_folders(values)
        csv_name = self.generate_csv_name(values)
        full_path = os.path.join(folder_path, csv_name)

        return CSVFileManager.write_to_csv(file_path=full_path, headers=headers)

    def read_csv_file(self, values: List[str]) -> List[List]:
        """
        Read a CSV file from the appropriate nested folder structure.

        Args:
            values (List[str]): List of values corresponding to the hierarchy levels.

        Returns:
            List[List]: Data read from the CSV file.
        """
        folder_path = self.create_nested_folders(values)
        csv_name = self.generate_csv_name(values)
        full_path = os.path.join(folder_path, csv_name)

        data = []
        with open(full_path, "r", newline="") as csvfile:
            reader = csv.reader(csvfile)
            data = list(reader)

        return data

    def create_dynamic_csv(
        self, constraints: Dict[str, str], file_type: str, dir_nesting_levels: int = 2
    ) -> tuple[str]:
        """
        Create a CSV file based on dynamic constraints and a file type.

        Args:
            constraints (Dict[str, str]): A dictionary of constraints (e.g., {"country": "CA", "state": "ON", "city": "Toronto"})
            file_type (str): The type of file (e.g., "animals")

        Returns:
            tuple[str]: CSV name, Full path to the created CSV file
            eg."animals_toronto_on_ca.py", "./csv/animals/toronto/ON/CA"
        """
        # Determine the hierarchy from the constraints
        self.hierarchy = list(constraints.keys())

        # Create the nested folders
        folder_path = self.create_nested_folders(
            list(constraints.values()[:dir_nesting_levels])
        )

        # Generate the CSV name
        csv_name = self.generate_dynamic_csv_name(constraints, file_type)

        # Create the full path
        full_path = os.path.join(folder_path, csv_name)

        return csv_name, full_path
