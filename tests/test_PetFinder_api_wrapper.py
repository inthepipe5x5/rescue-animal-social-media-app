import unittest
from unittest.mock import patch, MagicMock
import datetime
from ..Far_Fetched_App.PetFinderAPI.py import PetFinderPetPyAPI

class TestPetFinderPetPyAPI(unittest.TestCase):

    def setUp(self):
        self.api = PetFinderPetPyAPI()

    @patch('api_wrapper.Petfinder')
    def test_get_authentication_token(self, mock_petfinder):
        mock_response = MagicMock()
        mock_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_petfinder_instance = MagicMock()
        mock_petfinder_instance._authenticate.return_value = mock_response
        mock_petfinder.return_value = mock_petfinder_instance

        self.api.get_authentication_token()

        self.assertEqual(self.api.auth_token, 'test_token')
        self.assertIsInstance(self.api.auth_token_time, datetime.datetime)
        self.assertEqual(self.api.auth_token_expiry_time_in_seconds, 3600)

    @patch('api_wrapper.datetime')
    def test_validate_auth_token_valid(self, mock_datetime):
        mock_datetime.datetime.now.return_value = datetime.datetime(2024, 4, 10, 12, 0, 0)
        self.api.auth_token_time = datetime.datetime(2024, 4, 10, 11, 0, 0)
        jsonify_data = MagicMock(expires_in=3600)
        
        auth_token = self.api.validate_auth_token(jsonify_data)

        self.assertEqual(auth_token, jsonify_data.auth_token)

    @patch('api_wrapper.datetime')
    def test_validate_auth_token_expired(self, mock_datetime):
        mock_datetime.datetime.now.return_value = datetime.datetime(2024, 4, 10, 13, 0, 0)
        self.api.auth_token_time = datetime.datetime(2024, 4, 10, 11, 0, 0)
        jsonify_data = MagicMock(expires_in=3600)
        
        auth_token = self.api.validate_auth_token(jsonify_data)

        self.assertIsNone(auth_token)


if __name__ == '__main__':
    unittest.main()


    @patch('api_wrapper.Petfinder')
    def test_get_authentication_token(self, mock_petfinder):
        mock_response = MagicMock()
        mock_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_petfinder_instance = MagicMock()
        mock_petfinder_instance._authenticate.return_value = mock_response
        mock_petfinder.return_value = mock_petfinder_instance

        self.api.get_authentication_token()

        self.assertEqual(self.api.auth_token, 'test_token')
        self.assertIsInstance(self.api.auth_token_time, datetime.datetime)
        self.assertEqual(self.api.auth_token_expiry_time_in_seconds, 3600)

    @patch('api_wrapper.datetime')
    def test_validate_auth_token_valid(self, mock_datetime):
        mock_datetime.datetime.now.return_value = datetime.datetime(2024, 4, 10, 12, 0, 0)
        self.api.auth_token_time = datetime.datetime(2024, 4, 10, 11, 0, 0)
        jsonify_data = MagicMock(expires_in=3600)
        
        auth_token = self.api.validate_auth_token(jsonify_data)

        self.assertEqual(auth_token, jsonify_data.auth_token)

    @patch('api_wrapper.datetime')
    def test_validate_auth_token_expired(self, mock_datetime):
        mock_datetime.datetime.now.return_value = datetime.datetime(2024, 4, 10, 13, 0, 0)
        self.api.auth_token_time = datetime.datetime(2024, 4, 10, 11, 0, 0)
        jsonify_data = MagicMock(expires_in=3600)
        
        auth_token = self.api.validate_auth_token(jsonify_data)

        self.assertIsNone(auth_token)


if __name__ == '__main__':
    unittest.main()
