# arve-testbed-python

> [!WARNING]
> **INTENTIONALLY VULNERABLE CODE. DO NOT DEPLOY, DO NOT RUN ON A REACHABLE HOST,
> DO NOT COPY INTO REAL PROJECTS.**
> This repository contains deliberately planted SQL injection, command injection,
> path traversal, SSRF, unsafe deserialization, XSS, weak hashing, hardcoded
> credentials and vulnerable dependency pins. It exists only to evaluate the
> ARVE security scanner.

**All credentials in this repository and its Git history are synthetic.** They
were randomly generated and are correctly shaped, but they grant access to
nothing. No secret value appears in this README or in `EXPECTED_FINDINGS.md`,
which refer to file and line only.

## What it is

DocVault is a minimal Flask + `sqlite3` document service with 7 endpoints (upload,
download, search, convert, import-url, settings import, preview). Each endpoint
hosts plants from the matrix below. `expected-findings.json` is the answer key.
Conventions shared with the JS/TS, PHP and Java testbeds are in
[`TESTBED_SPEC.md`](TESTBED_SPEC.md), and the full plan is in [`plan.md`](plan.md).

## Plants

Generated from `expected-findings.json` by `scripts/render_answer_key.py`. Do not edit.

<!-- BEGIN PLANT TABLE -->
| ID | Kind | Location | Expected engines | Rule IDs | CWE | Cross-engine group |
|---|---|---|---|---|---|---|
| SAST-01 | sast | `app/search.py:19` | semgrep, codeql | `semgrep: arve.python.sql-injection, arve.python.sql-injection-taint`<br>`codeql: py/sql-injection` | CWE-89 | - |
| SAST-02 | sast | `app/convert.py:22` | semgrep, codeql | `semgrep: arve.python.command-injection, arve.python.command-injection-taint`<br>`codeql: py/command-line-injection` | CWE-78 | - |
| SAST-03 | sast | `app/docs.py:42` | semgrep, codeql | `semgrep: arve.python.path-traversal`<br>`codeql: py/path-injection` | CWE-22 | - |
| SAST-04 | sast | `app/fetch.py:22` | semgrep, codeql | `semgrep: arve.python.ssrf`<br>`codeql: py/full-ssrf` | CWE-918 | - |
| SAST-05 | sast | `app/fetch.py:12` | semgrep, codeql | `semgrep: arve.python.insecure-tls-verify-false`<br>`codeql: py/request-without-cert-validation` | CWE-295 | - |
| SAST-06 | sast | `app/settings.py:21` | semgrep, codeql | `semgrep: arve.python.unsafe-deserialization-pickle`<br>`codeql: py/unsafe-deserialization` | CWE-502 | - |
| SAST-07 | sast | `app/settings.py:14` | semgrep | `semgrep: arve.python.unsafe-yaml-load` | CWE-502 | - |
| SAST-08 | sast | `app/docs.py:25` | semgrep | `semgrep: arve.python.weak-hash-md5` | CWE-328 | - |
| SAST-09 | sast | `app/share.py:19` | semgrep | `semgrep: arve.python.weak-hash-sha1` | CWE-328 | - |
| SAST-10 | sast | `app/repository.py:25` | codeql | `codeql: py/sql-injection` | CWE-89 | - |
| SAST-11 | sast | `app/docs.py:54` | codeql | `codeql: py/reflective-xss` | CWE-79 | - |
| SEC-01 | secret | `app/share.py:12` | gitleaks, semgrep | `gitleaks: generic-api-key`<br>`semgrep: arve.generic.hardcoded-jwt-secret` | CWE-798 | C-01 |
| SEC-02 | secret | `app/config.py:10` | gitleaks, semgrep | `gitleaks: aws-access-token, generic-api-key`<br>`semgrep: arve.upstream.python.aws-secret-key` | CWE-798 | C-02 |
| SEC-03 | secret | `app/config.py:15` | semgrep, gitleaks | `semgrep: arve.python.hardcoded-password`<br>`gitleaks: generic-api-key` | CWE-259 | C-03 |
| SEC-04 | secret | `keys/signing.pem:2` | gitleaks | `gitleaks: private-key` | CWE-321 | - |
| SEC-05 | secret | `app/notify.py` (history only) | gitleaks | `gitleaks: generic-api-key` | CWE-798 | - |
| SEC-06 | secret | `docs/runbook.md:18` | gitleaks | `gitleaks: slack-webhook-url` | CWE-798 | - |
| DEP-01 | dependency | `requirements.txt` (Flask==2.2.5) | osv | `osv: GHSA-68rp-wp8r-4726, PYSEC-2026-2151` | - | - |
| DEP-02 | dependency | `requirements.txt` (Werkzeug==2.2.3) | osv | `osv: GHSA-29vq-49wr-vm6x, GHSA-2g68-c3qc-8985, GHSA-87hc-h4r5-73f7, GHSA-f9vj-2wh5-fj8j, GHSA-hgf8-39gv-g3f2, GHSA-hrfv-mqp8-q5rw, GHSA-q34m-jh98-gwm2, PYSEC-2023-221, PYSEC-2026-2043, PYSEC-2026-2044, PYSEC-2026-2045, PYSEC-2026-2046, PYSEC-2026-2320, PYSEC-2026-3417` | - | - |
| DEP-03 | dependency | `requirements.txt` (Jinja2==3.1.2) | osv | `osv: GHSA-cpwx-vrp4-4pq7, GHSA-gmj6-6f8f-6699, GHSA-h5c8-rqwp-cp95, GHSA-h75v-3vvj-5mfj, GHSA-q2x7-8rv6-6q7h, PYSEC-2026-1471, PYSEC-2026-1472, PYSEC-2026-1473, PYSEC-2026-1474, PYSEC-2026-1475` | - | - |
| DEP-04 | dependency | `requirements.txt` (requests==2.31.0) | osv | `osv: GHSA-9hjg-9r4m-mvj7, GHSA-9wx4-h78v-vm56, GHSA-gc5v-m9x4-r6x2, PYSEC-2026-1872, PYSEC-2026-1873, PYSEC-2026-2275` | - | - |
| SAFE-01 | control | `app/repository.py:7` | none (negative control) | - | - | - |
| SAFE-02 | control | `app/convert.py:24` | none (negative control) | - | - | - |
| SAFE-03 | control | `app/settings.py:24` | none (negative control) | - | - | - |
| SAFE-04 | control | `app/docs.py:27` | none (negative control) | - | - | - |
<!-- END PLANT TABLE -->

## How to scan

Requirements: Docker, Python 3, and a sibling checkout of ARVE at `../ARVE` for
the Semgrep rulepack. Override the path with `ARVE_RULES=<path to rules>`.

```bash
docker pull ghcr.io/gitleaks/gitleaks:v8.24.2
docker pull ghcr.io/google/osv-scanner:v1.9.2
docker pull semgrep/semgrep:1.90.0
docker build -t arve-codeql:2.27.1 ../ARVE/docker/codeql

python scripts/verify_plants.py --history          # all four engines + git history
python scripts/verify_plants.py --engines semgrep  # one engine
```

Each (plant, engine) prints `PASS`/`FAIL`, followed by `UNEXPECTED` findings and
`COUNT` mismatches against `expected_counts`. Raw reports land in `.scan/`.
Sanitised reference reports are committed in `baselines/`.

## How to score an ARVE run

Scan this repository (**including Git history**, since SEC-05 exists only there)
with ARVE, then compare its findings with `expected-findings.json`:

- **Recall**: each `positive` entry should be reported by each engine in
  `expected_engines`, at `file_path` within `line_start` … `line_start + line_span - 1`,
  under each rule in `rule_ids`. For DEP entries, match by package and version.
- **Correlation**: entries sharing a `cross_engine_group` are one secret seen by
  two engines. ARVE should correlate them rather than double-count.
- **False positives**: any finding on a `SAFE-*` line, or any finding not explained
  by an entry, is a false positive. `notes` in the key lists two known ARVE
  Semgrep false-positive patterns that the controls deliberately avoid.
- **Semgrep profile**: `-taint` rules exist only in ARVE's `extended` profile, and
  some rules are not in `ci`. Filter expectations by `semgrep_profile` and the
  rulepack manifest for the profile the run used.

## Maintenance

```bash
python scripts/render_answer_key.py           # markers -> JSON lines -> MD + this table
python scripts/seed_history.py --force        # rebuild the planted Git history (deletes .git)
python scripts/verify_plants.py --history --save-baselines
```
