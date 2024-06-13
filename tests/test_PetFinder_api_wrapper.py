import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from ..Far_Fetched_App.PetFinderAPI.py import PetFinderPetPyAPI

class TestPetFinderPetPyAPI(unittest.TestCase):

    def setUp(self):
        self.api = PetFinderPetPyAPI()


    def test_parse_breed(self):
        breeds_obj = {'primary': 'Labrador', 'secondary': 'Retriever', 'mixed': True, 'unknown': False}
        self.assertEqual(self.obj.parse_breed(breeds_obj), 'Labrador Retriever mix')

        breeds_obj = {'primary': 'Poodle', 'secondary': False, 'mixed': True, 'unknown': False}
        self.assertEqual(self.obj.parse_breed(breeds_obj), 'Poodle Mix')

        breeds_obj = {'primary': 'Siamese', 'secondary': False, 'mixed': False, 'unknown': False}
        self.assertEqual(self.obj.parse_breed(breeds_obj), 'Siamese')

        breeds_obj = {'unknown': True}
        self.assertEqual(self.obj.parse_breed(breeds_obj), 'Super Mutt')

    def test_parse_color(self):
        colors_obj = {'primary': 'Black', 'secondary': 'White', 'tertiary': 'Brown'}
        self.assertEqual(self.obj.parse_color(colors_obj), 'Black, White')

        colors_obj = {'primary': 'Calico', 'secondary': False, 'tertiary': False}
        self.assertEqual(self.obj.parse_color(colors_obj), 'Calico')

        colors_obj = {'primary': False}
        self.assertEqual(self.obj.parse_color(colors_obj), 'Unknown Color')

    def test_parse_photos(self):
        photos_list = [{'full': 'https://example.com/dog.jpg'}]
        self.assertEqual(self.obj.parse_photos(photos_list, 'dog'), 'https://example.com/dog.jpg')

        photos_list = []
        self.assertEqual(self.obj.parse_photos(photos_list, 'cat'), '../static/images/graphics/cat-freepik.png')

        self.assertEqual(self.obj.parse_photos(photos_list, 'invalid_type'), '../static/images/graphics/tracks_freepik.png')

    def test_parse_location_obj(self):
        loc_obj = {'city': 'New York', 'state': 'NY', 'country': 'USA'}
        self.assertEqual(self.obj.parse_location_obj(loc_obj), {'location': 'New York,NY', 'state': 'NY', 'country': 'USA', 'city': 'New York'})

        loc_obj = {'state': 'CA', 'country': 'USA'}
        self.assertEqual(self.obj.parse_location_obj(loc_obj), {'location': 'CA,USA', 'state': 'CA', 'country': 'USA'})

        loc_obj = {'country': 'Canada'}
        self.assertEqual(self.obj.parse_location_obj(loc_obj), {'location': 'Canada', 'country': 'Canada'})

    def test_parse_publish_date(self):
        pub_date = '2023-05-01T12:00:00+0000'
        # Calculate the expected delta based on the current date
        expected_delta = (datetime.now() - datetime.fromisoformat(pub_date.replace("+0000", "+00:00"))).days
        self.assertEqual(self.api.parse_publish_date(pub_date, action='delta'), expected_delta)
        self.assertEqual(self.api.parse_publish_date(pub_date, action='format'), '01/05/2023')

        self.assertIsNone(self.api.parse_publish_date(None, action='delta'))
        self.assertRaises(TypeError, self.api.parse_publish_date, pub_date, action='invalid')


if __name__ == '__main__':
    unittest.main()
