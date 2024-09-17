import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Project.app import app as application

if __name__ == "__main__":
    application.run()