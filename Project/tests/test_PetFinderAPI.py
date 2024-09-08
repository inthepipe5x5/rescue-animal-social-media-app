import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from package.PetFinderAPI import PetFinderPetPyAPI
from package.helper import get_anon_preference, get_user_preference

class TestPetFinderPetPyAPI(unittest.TestCase):

    def setUp(self):
        self.api = PetFinderPetPyAPI(get_anon_preference_func=get_anon_preference, get_user_preference_func=get_user_preference)


    def test_parse_breed(self):
        breeds_obj = {'primary': 'Labrador', 'secondary': 'Retriever', 'mixed': True, 'unknown': False}
        self.assertEqual(self.api.parse_breed(breeds_obj), 'Labrador Retriever mix')

        breeds_obj = {'primary': 'Poodle', 'secondary': False, 'mixed': True, 'unknown': False}
        self.assertEqual(self.api.parse_breed(breeds_obj), 'Poodle Mix')

        breeds_obj = {'primary': 'Siamese', 'secondary': False, 'mixed': False, 'unknown': False}
        self.assertEqual(self.api.parse_breed(breeds_obj), 'Siamese')

        breeds_obj = {'unknown': True}
        self.assertEqual(self.api.parse_breed(breeds_obj), 'Super Mutt')

    def test_parse_color(self):
        colors_obj = {'primary': 'Black', 'secondary': 'White', 'tertiary': 'Brown'}
        self.assertEqual(self.api.parse_color(colors_obj), 'Black, White')

        colors_obj = {'primary': 'Calico', 'secondary': False, 'tertiary': False}
        self.assertEqual(self.api.parse_color(colors_obj), 'Calico')

        colors_obj = {'primary': False}
        self.assertEqual(self.api.parse_color(colors_obj), 'Unknown Color')

    def test_parse_photos(self):
        photos_list = [{'full': 'https://example.com/dog.jpg'}]
        self.assertEqual(self.api.parse_photos(photos_list, 'dog'), 'https://example.com/dog.jpg')

        photos_list = []
        self.assertEqual(self.api.parse_photos(photos_list, 'cat'), '../static/images/graphics/cat-freepik.png')

        self.assertEqual(self.api.parse_photos(photos_list, 'invalid_type'), '../static/images/graphics/tracks_freepik.png')

    def test_parse_location_obj(self):
        loc_obj = {'city': 'New York', 'state': 'NY', 'country': 'USA'}
        self.assertEqual(self.api.parse_location_obj(loc_obj), {'location': 'New York,NY', 'state': 'NY', 'country': 'US', 'city': 'New York'})

        loc_obj = {'state': 'CA', 'country': 'USA'}
        self.assertEqual(self.api.parse_location_obj(loc_obj), {'location': 'CA,US', 'state': 'CA', 'country': 'US'})

        loc_obj = {'country': 'Canada'}
        self.assertEqual(self.api.parse_location_obj(loc_obj), {'location': 'CA', 'country': 'CA'})

    def test_parse_publish_date(self):
        #example published_date from PetFinder API response
        pub_date = '2024-05-01T12:00:00+0000' 
        
        # Calculate the expected delta based on the current date
        pub_date_obj = datetime.fromisoformat(pub_date.replace("+0000", "+00:00"))
        current_date_obj = datetime.now(timezone.utc)
        expected_delta = (current_date_obj - pub_date_obj).days
        
        self.assertEqual(self.api.parse_publish_date(pub_date, action='delta'), expected_delta) #date diff since June 14 2024

        self.assertRaises(TypeError, lambda: self.api.parse_publish_date(None, action='delta'))
        self.assertRaises(TypeError, lambda: self.api.parse_publish_date(None, action='invalid'))


if __name__ == '__main__':
    unittest.main()
