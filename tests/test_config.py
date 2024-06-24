import unittest
from flask import Flask

from Far_Fetched_App.app import app
from Far_Fetched_App.config import Config
from Far_Fetched_App.package.PetFinderAPI import PetFinderAPI
class TestApp(unittest.TestCase):
    """_summary_

    Args:
        unittest (_type_): _description_
    """

    def test_set_environment_command(runner):
        result = runner.invoke(args=["set-environment"])
        assert "default" in result.output
        
        result = runner.invoke(args=["set-environment", "--env", "development"])
        assert "development" in result.output
