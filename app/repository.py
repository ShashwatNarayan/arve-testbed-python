from . import queries


def get_document(conn, doc_id):
    cur = conn.cursor()
    # TESTBED SAFE-01
    cur.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    return cur.fetchone()


def insert_document(conn, title, filename, tag, md5, sha256):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO documents (title, filename, tag, md5, sha256) VALUES (?, ?, ?, ?, ?)",
        (title, filename, tag, md5, sha256),
    )
    conn.commit()
    return cur.lastrowid


def find_by_tag(conn, tag):
    sql = queries.tag_filter(tag)
    cur = conn.cursor()
    # TESTBED SAST-10
    cur.execute(sql)
    return cur.fetchall()
