import pickle

import yaml
from flask import Blueprint, jsonify, request

from . import config

bp = Blueprint("settings", __name__)


def load_defaults():
    with open(config.DEFAULTS_FILE, encoding="utf-8") as fh:
        # TESTBED SAST-07
        return yaml.load(fh, Loader=yaml.Loader)


@bp.post("/settings/import")
def import_settings():
    if request.mimetype == "application/x-docvault-bundle":
        # TESTBED SAST-06
        bundle = pickle.loads(request.get_data())
    else:
        # TESTBED SAFE-03
        bundle = yaml.safe_load(request.get_data())
    if not isinstance(bundle, dict):
        return jsonify({"error": "bundle must be a mapping"}), 400
    merged = {**load_defaults(), **bundle}
    return jsonify({"imported": sorted(bundle), "total": len(merged)})
