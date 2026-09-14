from flask import Flask

from . import config, db
from .convert import bp as convert_bp
from .docs import bp as docs_bp
from .fetch import bp as fetch_bp
from .search import bp as search_bp
from .settings import bp as settings_bp


def create_app():
    app = Flask(__name__)
    app.config["STORAGE_DIR"] = config.STORAGE_DIR
    app.config["DATABASE"] = config.DATABASE
    db.init_app(app)
    for blueprint in (docs_bp, search_bp, convert_bp, fetch_bp, settings_bp):
        app.register_blueprint(blueprint)
    return app
