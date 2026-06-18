import os
import atexit
import shutil

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config.settings import config_by_name

limiter = Limiter(key_func=get_remote_address, default_limits=["30 per minute"])


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "production")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    limiter.init_app(app)

    from .routes import bp
    app.register_blueprint(bp)

    atexit.register(_cleanup_upload_folder, app.config["UPLOAD_FOLDER"])

    return app


def _cleanup_upload_folder(folder):
    if os.path.isdir(folder):
        shutil.rmtree(folder, ignore_errors=True)
