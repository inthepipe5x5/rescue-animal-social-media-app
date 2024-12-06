from Project.api.routes.animals.animal_routes import animals_bp
from Project.api.routes.data.data_routes import data_bp
from Project.api.routes.user.user_routes import users_bp
from Project.api.routes.org.org_routes import orgs_bp
from Project.api.routes.error.error_routes import error_bp
from Project.api.routes.pf.pf_bp import pf_bp
from Project.api.routes.main.main_routes import main_bp


def register_bp(app):
    blueprints = [
        main_bp,
        animals_bp,
        orgs_bp,
        users_bp,
        data_bp,
        error_bp,
        pf_bp,
    ]

    for bp in blueprints:
        app.register_blueprint(
            bp,
            # set both to None to default to app template folder
            template_folder=None,
            static_folder=None,
        )
        app.logger.debug(
            f"Registered blueprint '{bp.name}' with template_folder={bp.template_folder}, static_folder={bp.static_folder}"
        )

    return app


if __name__ == "__main__":
    pass
