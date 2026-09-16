from flask import Blueprint, jsonify, request

from . import repository
from .db import get_db

bp = Blueprint("search", __name__)


@bp.get("/docs/search")
def search():
    conn = get_db()
    tag = request.args.get("tag")
    if tag:
        rows = repository.find_by_tag(conn, tag)
    else:
        q = request.args.get("q", "")
        cur = conn.cursor()
        # TESTBED SAST-01
        cur.execute(f"SELECT id, title FROM documents WHERE title LIKE '%{q}%'")
        rows = cur.fetchall()
    return jsonify([dict(row) for row in rows])
