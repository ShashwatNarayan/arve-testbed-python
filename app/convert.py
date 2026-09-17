import os
import subprocess

from flask import Blueprint, abort, current_app, jsonify, request

from . import repository
from .db import get_db

bp = Blueprint("convert", __name__)


@bp.post("/docs/<int:doc_id>/convert")
def convert(doc_id):
    row = repository.get_document(get_db(), doc_id)
    if row is None:
        abort(404)
    fmt = request.args.get("format", "pdf")
    out_dir = os.path.join(current_app.config["STORAGE_DIR"], "converted")
    os.makedirs(out_dir, exist_ok=True)
    src = os.path.join(current_app.config["STORAGE_DIR"], row["filename"])
    # TESTBED SAST-02
    status = os.system(f"soffice --headless --convert-to {fmt} --outdir {out_dir} {src}")
    # TESTBED SAFE-02
    info = subprocess.run(["file", "--brief", "--mime-type", src], capture_output=True, text=True)
    return jsonify({"ok": status == 0, "source_type": info.stdout.strip()})
