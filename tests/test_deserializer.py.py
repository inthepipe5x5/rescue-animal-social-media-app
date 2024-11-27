import unittest
import csv
import io
import os
import shutil

changed_org_keys = {
            "address.address1": "address1",
            "address.address2": "address2",
            "address.city": "city",
            "address.state": "state",
            "address.postcode": "postcode",
            "address.country": "country",
            "adoption.policy": "adoption_policy",
            "adoption.url": "adoption_url",
            "social_media.facebook": "facebook",
            "social_media.twitter": "twitter",
            "social_media.youtube": "youtube",
            "social_media.instagram": "instagram",
            "social_media.pinterest": "pinterest",
            "photos.full": "photo",
            "_links.self.href": "self_href",
            "_links.animals.href": "animals_href"
        }

class TestJSONFlattening(unittest.TestCase):
    def setUp(self):
        self.original_dict = {
            "organization": {
                "id": "NJ333",
                "name": "NJ333 - Petfinder Test Account",
                "email": "no-reply@petfinder.com",
                "phone": "555-555-5555",
                "address": {
                    "address1": "Test address 1",
                    "address2": "Test address 2",
                    "city": "Jersey City",
                    "state": "NJ",
                    "postcode": "07097",
                    "country": "US"
                },
                "hours": {
                    "monday": None,
                    "tuesday": None,
                    "wednesday": None,
                    "thursday": None,
                    "friday": None,
                    "saturday": None,
                    "sunday": None
                },
                "url": "https://www.petfinder.com/member/us/nj/jersey-city/nj333-petfinder-test-account/?referrer_id=d7e3700b-2e07-11e9-b3f3-0800275f82b1",
                "website": None,
                "mission_statement": None,
                "adoption": {
                    "policy": None,
                    "url": None
                },
                "social_media": {
                    "facebook": None,
                    "twitter": None,
                    "youtube": None,
                    "instagram": None,
                    "pinterest": None
                },
                "photos": [
                    {
                        "small": "https://photos.petfinder.com/photos/organizations/124/1/?bust=1546042081&width=100",
                        "medium": "https://photos.petfinder.com/photos/organizations/124/1/?bust=1546042081&width=300",
                        "large": "https://photos.petfinder.com/photos/organizations/124/1/?bust=1546042081&width=600",
                        "full": "https://photos.petfinder.com/photos/organizations/124/1/?bust=1546042081"
                    }
                ],
                "distance": None,
                "_links": {
                    "self": {
                        "href": "/v2/organizations/nj333"
                    },
                    "animals": {
                        "href": "/v2/animals?organization=nj333"
                    }
                }
            }
        }

        csv_data = "id,name,email,phone,address1,address2,city,state,postcode,country,url,website,mission_statement,adoption_policy,adoption_url,facebook,twitter,youtube,instagram,pinterest,photo,distance,self_href,animals_href"
        self.csv_reader = csv.reader(io.StringIO(csv_data))
        self.new_keys = next(self.csv_reader)

    def test_flattened_keys(self):
        for key in self.new_keys:
            self.assertIn(key, self.original_dict["organization"] or 
                               self.original_dict["organization"]["address"] or 
                               self.original_dict["organization"]["adoption"] or 
                               self.original_dict["organization"]["social_media"] or 
                               {"photo": True, "self_href": True, "animals_href": True},
                          f"Key '{key}' not found in original or expected structure")

    def test_removed_keys(self):
        removed_keys = ["hours", "photos", "_links"]
        for key in removed_keys:
            self.assertNotIn(key, self.new_keys, f"Removed key '{key}' found in new keys")

    def test_changed_keys(self):
        
        for old_key, new_key in changed_keys.items():
            self.assertIn(new_key, self.new_keys, f"Changed key '{new_key}' not found in new keys")
            self.assertNotIn(old_key.split('.')[-1], self.new_keys, f"Old key '{old_key.split('.')[-1]}' found in new keys")


import unittest
import json
import csv
import io

class TestJSONFlattening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load original dictionary
        with open('original_dict.json', 'r') as f:
            cls.original_dict = json.load(f)
        
        # Load new keys
        with open('new_keys.csv', 'r') as f:
            cls.new_keys = next(csv.reader(f))
        
        # Load test configuration
        with open('test_config.json', 'r') as f:
            cls.test_config = json.load(f)

    def test_flattened_keys(self):
        for key in self.new_keys:
            self.assertIn(key, self.original_dict["organization"] or 
                               self.original_dict["organization"]["address"] or 
                               self.original_dict["organization"]["adoption"] or 
                               self.original_dict["organization"]["social_media"] or 
                               {"photo": True, "self_href": True, "animals_href": True},
                          f"Key '{key}' not found in original or expected structure")

    def test_removed_keys(self):
        for key in self.test_config['removed_keys']:
            self.assertNotIn(key, self.new_keys, f"Removed key '{key}' found in new keys")

    def test_changed_keys(self):
        for old_key, new_key in self.test_config['changed_keys']:
            self.assertIn(new_key, self.new_keys, f"Changed key '{new_key}' not found in new keys")
            self.assertNotIn(old_key.split('.')[-1], self.new_keys, f"Old key '{old_key.split('.')[-1]}' found in new keys")

if __name__ == '__main__':
    unittest.main()



if __name__ == '__main__':
    unittest.main()
