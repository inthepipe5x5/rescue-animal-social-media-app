from flask import Blueprint

from .routes.animals import animals_bp
from .routes.data import datas_bp
from .routes.user import users_bp
from .routes.org import orgs_bp
from .routes.error import errors_bp
from .routes.pf import pf_bp


def register_bp(app):
    # Register blueprints
    app.register(animals_bp)
    app.register(orgs_bp)
    app.register(users_bp)
    app.register(datas_bp)
    app.register(errors_bp)
    app.register(pf_bp)

if __name__ == '__main__':
    pass