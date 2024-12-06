import sys
import os
#define project DIR
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) #renamed from BASE_DIR
# Add the project root directory to the Python path
sys.path.insert(0, PROJECT_DIR)

from Project.core.app import app

if __name__ == "__main__":
    print("Flask app =", app)
    app.run()
