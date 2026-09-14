import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STORAGE_DIR = os.environ.get("DOCVAULT_STORAGE", os.path.join(BASE_DIR, "storage"))
DATABASE = os.environ.get("DOCVAULT_DB", os.path.join(BASE_DIR, "docvault.db"))
DEFAULTS_FILE = os.path.join(BASE_DIR, "app", "defaults.yaml")

# TESTBED SEC-02
AWS_ACCESS_KEY_ID = "AKIA55BJ4I3KHMA4R4NO"
AWS_SECRET_ACCESS_KEY = "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"
ARCHIVE_BUCKET = "docvault-archive"

# TESTBED SEC-03
BACKUP_DB_PASSWORD = "yyeZWEkUy2t4fJmqRZYvgXjr"
BACKUP_DSN = f"postgresql://docvault:{BACKUP_DB_PASSWORD}@backup.docvault.internal/docvault"

MIRROR_URL = "https://mirror.docvault.internal"
SHARE_TTL_SECONDS = 7 * 24 * 3600
