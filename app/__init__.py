from .main.routes import main
from .auth.routes import auth
from .users.routes import users
from app import app


if __name__ == "__main__":
    print("Starting app")
    app.run(debug=True, use_reloader=True)
