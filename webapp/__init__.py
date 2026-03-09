from flask import Flask

from config import Config
from .routes import main_bp


def create_app(config_class=Config):
    """
    Application factory used by both local development and WSGI servers.
    """
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    # Load configuration
    app.config.from_object(config_class)

    # Ensure secret key is set for session management
    app.secret_key = app.config["SECRET_KEY"]

    # Register blueprints
    app.register_blueprint(main_bp)

    return app


