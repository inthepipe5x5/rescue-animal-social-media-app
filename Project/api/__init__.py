from Project.api.routes.animals.animal_routes import animals_bp
from Project.api.routes.data.data_routes import data_bp
from Project.api.routes.user.user_routes import users_bp
from Project.api.routes.org.org_routes import orgs_bp
from Project.api.routes.error.error_routes import error_bp
from Project.api.routes.pf.pf_bp import pf_bp


def register_bp(app):
    # Register blueprints
    app.register(animals_bp)
    app.register(orgs_bp)
    app.register(users_bp)
    app.register(data_bp)
    app.register(error_bp)
    app.register(pf_bp)


if __name__ == "__main__":
    pass
