import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

# Create the application instance
app = create_app()


if __name__ == "__main__":
    print("Flask app =", app)
    app.run()
