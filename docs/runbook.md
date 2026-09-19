# DocVault runbook

## Start

    pip install -r requirements.txt
    flask --app run run

## Storage

Uploaded files live in `storage/` (override with `DOCVAULT_STORAGE`). The SQLite
database defaults to `docvault.db` (override with `DOCVAULT_DB`).

## Alerts

Conversion failures are posted to the #docvault-ops channel via this webhook:

<!-- TESTBED SEC-06 -->
    https://hooks.slack.com/services/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
