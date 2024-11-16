from flask import Blueprint

from Project.routes.animals import animals_bp
from Project.routes.data import datas_bp
from Project.routes.user import users_bp
from Project.routes.org import orgs_bp
from Project.routes.error import errors_bp
from Project.routes.pf import pf_bp


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