from pathlib import Path

from flask import Flask

from .config import Config
from .extensions import db, login_manager
from .models import User


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_class)

    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Войдите в аккаунт, чтобы открыть эту страницу."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .routes import main_bp, auth_bp, trip_bp
    from .api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(trip_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()

    return app
