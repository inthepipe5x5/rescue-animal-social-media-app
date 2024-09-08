#!/bin/bash

# Set the path to your Flask app
export FLASK_APP=$(pwd)/Project/app.py

# Set the Flask environment (production or development)
export FLASK_ENV=production

# Change to the directory containing the wsgi.py file
cd Project

# Start Gunicorn
exec gunicorn --log-level=info --bind 0.0.0.0:8000 wsgi:app