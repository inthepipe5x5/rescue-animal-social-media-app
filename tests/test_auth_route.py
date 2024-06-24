import unittest
from flask import Flask
from flask.testing import FlaskClient

from ..Far_Fetched_App.app import app  # Import your Flask app
from ..Far_Fetched_App.models import db, User  # Import your Flask app

from sqlalchemy.exc import IntegrityError


class TestAuthRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True #Enable testing mode
        self.app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing
        self.client = self.app.test_client()

        # Create all tables
        with self.app.app_context():
            db.create_all()

        self.test_user_data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "testpassword123",
            "confirm_password": "testpassword123",
            "bio": "testbio123",
            "state": "teststate123",
            "country": "testcountry123",
            "rescue_action_type": "adoption",
            "animal_types": ["dog", "cat"],
        }

    def tearDown(self):
        # Remove all tables after each test
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_signup_get(self):
        response = self.client.get("/signup")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Sign me up!", html)


    def test_signup_success(self):
        response = self.client.post(
            "/signup", data=self.test_user_data, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Account created successfully", response.data)

    def test_signup_existing_user(self):
        # First, create a user
        self.client.post("/signup", data=self.test_user_data)

        # Try to create the same user again
        response = self.client.post(
            "/signup", data=self.test_user_data, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Username already taken", response.data)

    def test_login_get(self):
        response = self.client.get("/login")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Log in", html)


    def test_login_success(self):
        # First, create a user
        self.client.post("/signup", data=self.test_user_data)

        # Now try to log in
        login_data = {
            "username": self.test_user_data["username"],
            "password": self.test_user_data["password"],
        }
        response = self.client.post("/login", data=login_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Log out", response.data)

    def test_login_invalid_credentials(self):
        login_data = {"username": "nonexistentuser", "password": "wrongpassword"}
        response = self.client.post("/login", data=login_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid credentials.", response.data)

    def test_signup_missing_fields(self):
        incomplete_data = self.test_user_data.copy()
        del incomplete_data["username"]  # Remove username field
        response = self.client.post(
            "/signup", data=incomplete_data, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"This field is required", response.data)

    def test_signup_invalid_email(self):
        invalid_email_data = self.test_user_data.copy()
        invalid_email_data["email"] = "invalid_email"
        response = self.client.post(
            "/signup", data=invalid_email_data, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid email address", response.data)


if __name__ == "__main__":
    unittest.main()
