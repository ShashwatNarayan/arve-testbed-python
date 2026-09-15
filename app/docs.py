import hashlib
import os
import uuid

from flask import Blueprint, Response, abort, current_app, jsonify, request
from markupsafe import escape

from . import repository, share
from .db import get_db

bp = Blueprint("docs", __name__)


@bp.post("/docs")
def upload():
    upload = request.files.get("file")
    if upload is None:
        abort(400)
    data = upload.read()
    stored_name = uuid.uuid4().hex
    dest = os.path.join(current_app.config["STORAGE_DIR"], stored_name)
    with open(dest, "wb") as fh:
        fh.write(data)
    # TESTBED SAST-08
    md5 = hashlib.md5(data).hexdigest()
    # TESTBED SAFE-04
    sha256 = hashlib.sha256(data).hexdigest()
    doc_id = repository.insert_document(
        get_db(), request.form.get("title", "untitled"), stored_name,
        request.form.get("tag"), md5, sha256,
    )
    return jsonify({"id": doc_id, "md5": md5, "sha256": sha256, "share": share.share_link(doc_id)}), 201


@bp.get("/docs/<int:doc_id>/download")
def download(doc_id):
    row = repository.get_document(get_db(), doc_id)
    if row is None:
        abort(404)
    name = request.args.get("name") or row["filename"]
    # TESTBED SAST-03
    with open(os.path.join(current_app.config["STORAGE_DIR"], name), "rb") as fh:
        data = fh.read()
    return Response(data, mimetype="application/octet-stream")


@bp.get("/docs/<int:doc_id>/preview")
def preview(doc_id):
    row = repository.get_document(get_db(), doc_id)
    if row is None:
        abort(404)
    highlight = request.args.get("highlight", "")
    # TESTBED SAST-11
    return Response(f"<h1>{escape(row['title'])}</h1><p class=\"match\">{highlight}</p>", mimetype="text/html")
