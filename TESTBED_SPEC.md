# Testbed spec: shared conventions for `arve-testbed-*`

Written in `arve-testbed-python` (the template) and copied **verbatim** into the
JS/TS, PHP and Java testbeds. To change a convention, change it here first, in the
Python repo, then re-copy it.

## 1. Purpose

Each testbed is a small, deliberately vulnerable app (DocVault, 7 endpoints) with
a machine-readable answer key. ARVE scans it, and its findings are scored against
the key for recall (positive plants found) and false positives (negative controls
and unexpected findings).

## 2. Engines and pinned versions

These must match `ARVE/backend/app/core/config.py`. Re-check them whenever a repo is
built or rebaselined.

| Engine | Image | Notes |
|---|---|---|
| Gitleaks | `ghcr.io/gitleaks/gitleaks:v8.24.2` | `dir` over the working tree; `git` over history (`--history`) |
| OSV-Scanner | `ghcr.io/google/osv-scanner:v1.9.2` | recursive lockfile scan |
| Semgrep | `semgrep/semgrep:1.90.0` | **ARVE's rulepack only** (`ARVE/backend/app/security/semgrep/rules`), never `--config auto` |
| CodeQL | `arve-codeql:2.27.1` | ARVE wrapper, `security-extended` |

Plant only what one of these engines actually detects. Every SAST plant maps to a
real ARVE Semgrep rule ID or a CodeQL `security-extended` query ID.

## 3. Finding IDs

| Prefix | Meaning | Engines |
|---|---|---|
| `SAST-NN` | code flaw | Semgrep and/or CodeQL |
| `SEC-NN` | hardcoded secret | Gitleaks (some also Semgrep) |
| `DEP-NN` | vulnerable dependency | OSV-Scanner |
| `SAFE-NN` | negative control: must produce **no** finding | all |

## 4. Markers

Put a comment holding the ID **only** on the line directly above each plant. Use
the file's own comment syntax:

    # TESTBED SAST-03          (Python, YAML, requirements.txt, PEM preamble)
    // TESTBED SAST-03         (JS/TS/Java/PHP)
    <!-- TESTBED SEC-06 -->    (Markdown)

The plant is the first non-blank line after the marker. Never describe the flaw in
the marker: ARVE's LLM layer reads the surrounding code. Do not obfuscate either.
Difficulty comes from location, cross-file flow and cross-engine overlap.

## 5. Answer key

`expected-findings.json` is the **only** hand-edited answer key. Write each entry
as its plant goes in. `scripts/render_answer_key.py` fills `file_path`/`line_start`
from the markers and generates `EXPECTED_FINDINGS.md` and the README plant table.

Top level: `schema_version` (`"2.0"`), `repository`, `language`,
`advisory_data_verified`, `scanners`, `engine_expectations` (`run` | `skipped`
per engine, e.g. `"codeql": "skipped"` for PHP), `expected_counts`
(working-tree findings per engine, plus `gitleaks_history`), `findings[]` and `notes[]`.

Each finding:

| Field | Meaning |
|---|---|
| `id`, `kind` | ID; `positive` or `negative` |
| `finding_type` | `sast` \| `secret` \| `dependency` \| `control` |
| `expected_engines` | engines that must report it (empty for controls) |
| `rule_ids` | `{engine: id or [ids]}`. Each listed ID must be observed. Use what the scanner **actually** reports, not what was expected. For OSV, this is the full advisory ID list. |
| `semgrep_profile` | lowest ARVE profile with the rule (`ci` ⊂ `standard` ⊂ `extended`) |
| `cwe` | primary CWE |
| `file_path`, `line_start` | generated from the marker |
| `line_span` | lines covered from `line_start` (default 1), e.g. a key pair on 2 lines |
| `cross_engine_group` | `C-NN` when two engines report the same secret location (tests ARVE correlation/dedup) |
| `history_only`, `history` | for secrets that exist only in Git history: `{file_path, line_start, introduced_in, removed_in}` |
| `package`, `version`, `ecosystem` | DEP entries only |
| `notes` | anything a reviewer needs, in particular why an engine is *not* expected |

## 6. Credentials

- Synthetic, random and correctly shaped. Never documented example keys.
- AWS access key IDs use the base32 alphabet (`AKIA` + 16 of `A-Z2-7`).
- Gitleaks `generic-api-key` needs keyword and value on the same line.
- Generate RSA keys with `openssl genrsa -traditional`.
- **No secret value in any `.md` file** except a deliberate non-code plant (the
  runbook). The answer key, README and generated MD hold file + line only.
- One history-only secret per repo. `seed_history.py` derives its value from a
  seed, so it never sits at HEAD.
- Committed baselines are sanitised (no SARIF snippets, gitleaks redacted), so
  they add no findings.

## 7. Scripts (copied from the template; only the marked parts change per language)

| Script | Language-specific part |
|---|---|
| `scripts/verify_plants.py` | none (reads everything from the answer key) |
| `scripts/render_answer_key.py` | none |
| `scripts/seed_history.py` | `COMMITS`, `HISTORY_ONLY` and the history-only file template |

`verify_plants.py` prints one line per (plant, engine), then `UNEXPECTED` and
`COUNT` lines, and exits non-zero on any of them. Raw reports go to `.scan/`
(gitignored) and are never pasted anywhere. `--save-baselines` writes sanitised
copies to `baselines/`.

## 8. Known engine behaviour (learned in the Python build)

- Semgrep OSS taint is intraprocedural. A source and sink in different functions
  are CodeQL-only, which is how the cross-file SAST plant works.
- Semgrep `"..."` positional patterns do not match keyword arguments. Its constant
  propagation does match a local bound to a literal.
- ARVE's `sql-injection-taint` sink is the whole `execute(...)` call, so
  parameterized queries fed from a source are reported (a known false positive).
  Controls avoid it.
- CodeQL (Python) does not treat the return value of a Flask Blueprint `.get()` /
  `.post()` view as an HTTP response. Return an explicit `Response(...)` for XSS
  plants.
- An `arve-codeql` image built from a Windows checkout has a CRLF wrapper.
  `verify_plants.py` strips the CRs at run time.
