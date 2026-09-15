import hashlib
import time

import jwt

from . import config


def download_ticket(doc_id):
    claims = {"doc": doc_id, "exp": int(time.time()) + config.SHARE_TTL_SECONDS}
    # TESTBED SEC-01
    signing_key = "wx248P9n6nULWGxa8ggBNFgWpnsdjXE1"
    return jwt.encode(claims, signing_key, algorithm="HS256")


def share_link(doc_id):
    issued = int(time.time())
    # TESTBED SAST-09
    digest = hashlib.sha1(f"{doc_id}:{issued}".encode()).hexdigest()
    return f"/docs/{doc_id}/download?t={digest}&ts={issued}"
