LIST_COLUMNS = "id, title, tag, created_at"


def tag_filter(tag):
    return "SELECT " + LIST_COLUMNS + " FROM documents WHERE tag = '" + tag + "' ORDER BY created_at DESC"
