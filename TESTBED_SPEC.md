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

    # TESTBED SAST-03          (Python, YAML, .properties, requirements.txt, PEM preamble)
    // TESTBED SAST-03         (JS/TS/Java/PHP)
    <!-- TESTBED SEC-06 -->    (Markdown, XML: pom.xml)

The plant is the first non-blank line after the marker. Files that cannot hold a
comment (JSON: `package.json`, `package-lock.json`, `composer.lock`) take no marker;
their entry carries a `locator` string instead, e.g. `"node_modules/qs"`, and
the first line of `file_path` containing it is the plant. Never describe the flaw in
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
| `expected_engines` | engines that must report it (empty for controls, and for a known miss: a plant no engine can report under ARVE's current setup, explained in `notes`) |
| `rule_ids` | `{engine: id or [ids]}`. Each listed ID must be observed. Use what the scanner **actually** reports, not what was expected. For OSV, this is the full advisory ID list. |
| `semgrep_profile` | lowest ARVE profile with the rule (`ci` ⊂ `standard` ⊂ `extended`) |
| `cwe` | primary CWE |
| `file_path`, `line_start` | generated from the marker |
| `locator` | for files with no comment syntax: the substring that identifies the plant line |
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
- ARVE rulepack gap (JS/TS): `arve.javascript.sql-injection` only matches
  `$DB.query(...)`. better-sqlite3 has no `.query` (it uses `prepare`/`exec`), so
  SQL injection through better-sqlite3 is CodeQL-only. CodeQL models better-sqlite3.
- ARVE's JS command-injection rule matches a bare `exec(...)` call, i.e. one
  imported with `import { exec } from "child_process"`, not `child_process.exec(...)`.
- ARVE rulepack gap (PHP): the `sql-injection`, `command-injection` and
  `path-traversal` rules need a string literal as the left operand of a single
  concatenation, `f("..." . $X)`. A three-part concatenation (`"a" . $x . "b"`), a
  constant or `__DIR__` prefix, or an argument built in a variable is not matched.
  Plants use the exact two-operand shape.
- Known ARVE false positive (PHP): the same rules accept any `$X`, so
  `shell_exec("cmd " . escapeshellarg($x))` and
  `file_get_contents("dir/" . basename($x))` are reported. Controls bind the
  argument to a variable first.
- CodeQL has no PHP extractor. The PHP testbed sets `engine_expectations.codeql`
  to `skipped`; the correct ARVE outcome is a `COMPLETED` scan with CodeQL skipped.
- An `arve-codeql` image built from a Windows checkout has a CRLF wrapper.
  `verify_plants.py` strips the CRs at run time.
- ARVE sandbox gap (Java): the CodeQL wrapper extracts Java with `--build-mode=none`,
  the image has no Maven and the sandbox has no network, so dependency jars are never
  resolved. Spring types stay unknown and `@RequestParam` / `@RequestBody` are not
  taint sources: every taint query (SQL injection, command injection, path injection,
  SSRF, unsafe deserialization, XSS) is silent. Only queries that need the JDK alone
  fire (`java/insecure-trustmanager`, `java/weak-cryptographic-algorithm`,
  `java/relative-path-command`). The Java testbed still plants the taint flaws and
  records them as known misses with empty `expected_engines`. They become expected
  once ARVE resolves Java dependencies offline. With network access the same image
  reports all of them.
- CodeQL false positives (Java, seen only with dependencies resolved):
  `java/command-line-injection` reports any request string passed to `ProcessBuilder`,
  including an argument list with no shell, and `java/unsafe-deserialization` reports
  `ObjectInputStream.readObject` even behind an `ObjectInputFilter` allowlist.
  Controls use a numeric argument and a non-serialization format instead.
- `java/relative-path-command` reports a command named without a path (`"sh"`).
  Plants and controls use absolute paths.
- Maven Central answers osv-scanner's Go HTTP client with `429` after a handful of
  requests (`Retry-After` of about 28 minutes). A `pom.xml` with a parent POM or an
  imported BOM then fails to resolve, and osv-scanner exits 128 with "No package
  sources found": zero findings, not an error ARVE can tell from a clean repo. A
  parent-less `pom.xml` with explicit versions resolves through deps.dev alone and
  is not affected, so the Java testbed uses no Spring Boot parent.
