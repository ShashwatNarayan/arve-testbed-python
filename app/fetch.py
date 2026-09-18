import os
import uuid

import requests
from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("fetch", __name__)


def mirror_available():
    # TESTBED SAST-05
    resp = requests.get("https://mirror.docvault.internal/health", verify=False, timeout=3)
    return resp.ok


@bp.post("/docs/import-url")
def import_url():
    url = (request.get_json(silent=True) or {}).get("url", "")
    if not url:
        return jsonify({"error": "url is required"}), 400
    # TESTBED SAST-04
    resp = requests.get(url, timeout=10)
    stored_name = uuid.uuid4().hex
    dest = os.path.join(current_app.config["STORAGE_DIR"], stored_name)
    with open(dest, "wb") as fh:
        fh.write(resp.content)
    return jsonify({"stored": stored_name, "bytes": len(resp.content),
                    "mirror": mirror_available()}), 201
