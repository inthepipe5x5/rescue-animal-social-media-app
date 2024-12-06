from Project.api.routes.animals.animal_routes import animals_bp
from Project.api.routes.data.data_routes import data_bp
from Project.api.routes.user.user_routes import users_bp
from Project.api.routes.org.org_routes import orgs_bp
from Project.api.routes.error.error_routes import error_bp
from Project.api.routes.pf.pf_bp import pf_bp
from Project.api.routes.main.main_routes import main_bp

def register_bp(app):
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(animals_bp)
    app.register_blueprint(orgs_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(error_bp)
    app.register_blueprint(pf_bp)
    
    return app


if __name__ == "__main__":
    pass
