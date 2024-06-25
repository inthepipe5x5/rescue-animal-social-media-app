import unittest
from flask import Flask

from ..FarFetched.app import app
from ..FarFetched.config import Config
from ..FarFetched.package.PetFinderAPI import PetFinderAPI
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
