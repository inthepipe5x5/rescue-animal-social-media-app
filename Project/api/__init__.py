from flask import Blueprint

from .routes.animals import animal_routes
from .routes.data import data_routes
from .routes.user import user_routes
from .routes.org import org_routes

api_bp = Blueprint('api', __name__)

def init_api(app):
    animal_routes.register(api_bp)
    org_routes.register(api_bp)
    user_routes.register(api_bp)
    
    app.register_blueprint(api_bp, url_prefix='/api')

if __name__ == '__main__':
    pass