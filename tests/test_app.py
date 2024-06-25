import os

import unittest
from flask import Flask, session

from ..FarFetched.app import app
from ..FarFetched.config import Config, config


class TestApp(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_index_route(self):
        """
        Test the index route
        """
        response = self.app.get("/")
        self.assertEqual(response.status_code, 200)

    def test_initial_session_function(self):
        """
        The function tests if the initial key-value pairs are set correctly in the Flask session.
        """
        with app.test_client() as client:
            # Make a request to trigger session handling
            client.get('/')

            # Check if the session values are set correctly
            with client.session_transaction() as session:
                # define the expected initial session values
                default_session_keys = {
                    "location": os.environ.get("CURR_LOCATION", "ON,CA"),
                    "state": os.environ.get("state", "ON"),
                    "country": os.environ.get("country", "CA"),
                    "animal_types": os.environ.get("animal_types", "dog").split(','),
                }
                for key, value in default_session_keys.items():
                    self.assertEqual(session[key], value)
                #expect no user_id is saved in session
                self.assertFalse("CURR_USER_KEY" in session)

if __name__ == "__main__":
    unittest.main()
