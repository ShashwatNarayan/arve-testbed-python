# Plan — ARVE multi-language testbeds (`arve-testbed-*`)

**Owner:** Shashwat · **Drafted:** 2026-10-03 · **Status:** awaiting team sign-off

Four deliberately vulnerable repositories, one per language, each with a
machine-readable answer key, so the team can score ARVE per engine (precision /
recall) instead of eyeballing results. Same idea as `arve-ledger-testbed`, but
now covering all four engines that are live in ARVE.

---

## 0. TL;DR

- **One app, four languages.** Every repo implements the same tiny app
  ("DocVault", §2). Same features → findings are comparable across languages,
  and the spec is written once.
- **Repo 1 (Python) is built first and goes through a team approval gate.**
  Repos 2–4 are not started until it passes (§3). They are *ports* of repo 1,
  which is where most of the token savings come from.
- **Only plant what ARVE's engines can actually detect** — the exact rule IDs in
  ARVE's rulepack, not "things that are generally insecure".
- **Every repo is pushed to its own GitHub repo** (§9).
- **Two Claude usage windows for all four:** Python in window A, the three ports
  in window B (§6). Token rules in §7.
- **Kickstart prompts for all four repos are in §11.**

---

## 1. Engine coverage — what each repo can and cannot test

ARVE currently runs four engines (Phase 4A complete). Testbeds must match their
pinned versions, otherwise baselines drift and real ARVE bugs look like testbed
bugs.

| Engine | ARVE-pinned version | Finds |
|---|---|---|
| Gitleaks | `v8.24.2` | Secrets in working tree (+ history) |
| OSV-Scanner | `v1.9.2` | Vulnerable deps from lockfiles |
| Semgrep | `1.90.0` + ARVE rulepack `2026.09.1` (27 rules) | Pattern / taint SAST |
| CodeQL | `arve-codeql:2.27.1`, `security-extended` | Interprocedural SAST |

> Confirm these against `backend/app/core/config.py` on the day each repo is
> built — versions may have moved since this plan was written.

Coverage per language, which is what decides the plant list:

| Language | Gitleaks | OSV (lockfile) | Semgrep ARVE rules | CodeQL |
|---|---|---|---|---|
| Python | ✅ | `requirements.txt` | 15 rules (incl. 2 taint) | ✅ |
| JS / TS | ✅ | `package-lock.json` | 6 rules (JS + TS) | ✅ |
| Java | ✅ | `pom.xml` (Maven) | **0 rules** | ✅ |
| PHP | ✅ | `composer.lock` | 4 rules | ❌ not supported |

Java and PHP are mirror images, and both gaps are useful rather than problems:

- **PHP** has Semgrep rules but no CodeQL support → tests that ARVE reports
  CodeQL as **skipped** and the scan still ends `COMPLETED`, not `PARTIAL` / `FAILED`.
- **Java** has CodeQL support but no ARVE Semgrep rules → all Java SAST plants are
  **CodeQL-only**, and Semgrep must run, succeed, and report zero findings.

Neither repo should be read as "ARVE is weak at this language" — it's a
statement about the current rulepack, and the answer key says so explicitly.

---

## 2. The app — DocVault

A minimal document-sharing service. SQLite, no auth, no admin, no frontend beyond
what a plant needs. **Seven endpoints, ~12 source files per repo.** Complexity
budget goes to the plant matrix, never the architecture.

| # | Endpoint | Realistic reason for the plant it hosts |
|---|---|---|
| 1 | `POST /docs` | upload — checksum computed (weak hash) |
| 2 | `GET /docs/{id}/download?name=` | read file from disk (path traversal) |
| 3 | `GET /docs/search?q=` | title search (SQL injection) |
| 4 | `POST /docs/{id}/convert?format=` | shell out to a converter (command injection) |
| 5 | `POST /docs/import-url` | fetch a remote doc (SSRF, TLS verify off) |
| 6 | `POST /settings/import` | import a settings bundle (unsafe deserialization / eval) |
| 7 | `GET /docs/{id}/preview` | render title as HTML (XSS) |

Framework per language — chosen so ARVE's taint sources and CodeQL's remote-flow
models actually fire:

| Repo | Stack | Why |
|---|---|---|
| `arve-testbed-python` | Flask + `sqlite3` | ARVE taint rules source from `flask.request.args.get(...)` |
| `arve-testbed-js` | Express server in **TypeScript** (run via `tsx`) + `better-sqlite3`, one static page in plain **JS** | Express `req.query` is CodeQL's standard JS source; plants split across `.ts` and `.js` so both extensions are exercised |
| `arve-testbed-java` | Spring Boot (`web` starter only) + plain JDBC + `sqlite-jdbc`, Maven | Spring is CodeQL's best-modelled Java framework; raw JDBC `Statement` gives the classic SQLi sink |
| `arve-testbed-php` | plain PHP 8 + PDO SQLite + Composer | no framework; matches ARVE's `$db->query()` patterns |

---

## 3. Rollout and the approval gate

```
Repo 1: arve-testbed-python  ──►  GATE (team review + ARVE scan)  ──►  Repos 2–4 (ports)
```

Python goes first because it has the richest coverage (all four engines, 15
Semgrep rules incl. taint) and matches the stack the team already knows. If the
template has a flaw, Python is where it shows; finding it here means fixing it
once instead of four times.

After the gate: **JS/TS → PHP → Java.** Java goes last because it's the only
one with real build-tooling risk (CodeQL build mode, Maven resolution); by then the
template is settled and the only new problems are Java-specific.

**Gate — repo 1 is approved when:**

- [ ] Clean skeleton commit scanned with all four reference tools → **zero findings**
- [ ] Every positive plant detected by every engine listed for it in the answer key
- [ ] Every negative control (`SAFE-*`) produces **zero** findings
- [ ] Line numbers in the answer key are generated from markers, not hand-written
- [ ] All four baseline files committed
- [ ] ARVE itself scanned the repo and the team has the diff vs. the answer key
- [ ] Team agrees on schema and conventions — **frozen after this point**
- [ ] Pushed to GitHub

Any change to conventions after the gate means re-touching repo 1 — so argue
about them before approval, not after.

---

## 4. Shared conventions (all four repos)

These live in `TESTBED_SPEC.md`, written in repo 1 and **copied verbatim** into
repos 2–4. The prompts reference it instead of restating it.

### 4.1 Finding IDs

| Prefix | Meaning | Engines |
|---|---|---|
| `SAST-NN` | code flaw | Semgrep and/or CodeQL |
| `SEC-NN` | hardcoded secret | Gitleaks (some also Semgrep) |
| `DEP-NN` | vulnerable dependency | OSV-Scanner |
| `SAFE-NN` | negative control — must produce **no** finding | all |

`SAFE-*` controls are new compared with the ledger testbed. Without them we can
measure recall but not false positives.

### 4.2 Markers instead of hand-maintained line numbers

Each plant gets a neutral comment on the line **directly above** it:

```
# TESTBED SAST-03
```

Only the ID — no description like "SQL injection here", since ARVE's LLM layer
reads surrounding code and a descriptive marker leaks the answer.
`scripts/render_answer_key.py` reads the markers and fills `line_start` into the
JSON automatically. This removes the separate "verify every line number" pass the
ledger build needed.

### 4.3 Answer key — single source of truth

`expected-findings.json` is the only file edited by hand. `EXPECTED_FINDINGS.md`
and the plant table in `README.md` are **generated** from it by the render
script. Schema = ledger schema `1.0` plus:

```json
{
  "id": "SAST-01",
  "kind": "positive",
  "finding_type": "sast",
  "expected_engines": ["semgrep", "codeql"],
  "rule_ids": { "semgrep": "arve.python.sql-injection", "codeql": "py/sql-injection" },
  "semgrep_profile": "standard",
  "cwe": "CWE-89",
  "file_path": "app/search.py",
  "line_start": 0,
  "cross_engine_group": null,
  "notes": "..."
}
```

Plus a repo-level `engine_expectations` block, e.g. `"codeql": "skipped"` for PHP.
CodeQL query IDs in §5 are *expected*; the build must replace them with what the
SARIF actually reports.

### 4.4 Credentials

Same rules as the ledger testbed, which were learned the hard way:
synthetic, random, correctly shaped; no documented example keys; AWS IDs use
the base32 alphabet; `generic-api-key` needs keyword and value on one line; RSA
keys generated with `openssl`. **Secret values never appear in any `.md` file** —
answer key references file + line only, or Gitleaks flags the README.

### 4.5 Repo layout (identical shape across languages)

```
arve-testbed-<lang>/
├── README.md                 warning + generated plant table + how to scan/score
├── TESTBED_SPEC.md           shared conventions (copied from repo 1)
├── EXPECTED_FINDINGS.md      generated
├── expected-findings.json    ★ hand-edited source of truth
├── baselines/                gitleaks.json, osv.json, semgrep.sarif, codeql.sarif
├── scripts/
│   ├── verify_plants.py      runs the 4 reference scanners via Docker, ARVE-pinned
│   ├── render_answer_key.py  markers → JSON lines → MD + README table
│   └── seed_history.py       rebuilds the planted Git history
├── app/ (or src/, cmd/)      the seven endpoints
├── docs/runbook.md           non-code secret location
└── .github/workflows/ci.yml  workflow-YAML secret location
```

`scripts/` is copied from repo 1; only the language-specific bits change.

---

## 5. Plant matrices

Targets, not final — each must be verified by its reference scanner **at the
moment it is planted**. "C" = cross-engine group (same location, two engines;
tests ARVE's correlation/dedup).

### 5.1 Python — `arve-testbed-python` (~21 plants + 4 controls)

| ID | Plant | Expected engines |
|---|---|---|
| SAST-01 | f-string SQL in `cursor.execute` from `request.args` | Semgrep `sql-injection` + `sql-injection-taint`, CodeQL `py/sql-injection` |
| SAST-02 | `os.system` with request arg | Semgrep `command-injection` (+taint), CodeQL `py/command-line-injection` |
| SAST-03 | `open(os.path.join(DIR, name))` | Semgrep `path-traversal`, CodeQL `py/path-injection` |
| SAST-04 | `requests.get(user_url)` | Semgrep `ssrf`, CodeQL `py/full-ssrf` |
| SAST-05 | `requests.get(..., verify=False)` | Semgrep `insecure-tls-verify-false`, CodeQL `py/request-without-cert-validation` |
| SAST-06 | `pickle.loads` on uploaded bundle | Semgrep `unsafe-deserialization-pickle`, CodeQL `py/unsafe-deserialization` |
| SAST-07 | `yaml.load` without SafeLoader | Semgrep `unsafe-yaml-load` |
| SAST-08 | `hashlib.md5` file checksum | Semgrep `weak-hash-md5` |
| SAST-09 | `hashlib.sha1` share-link token | Semgrep `weak-hash-sha1` |
| SAST-10 | SQL built in a helper in another module, executed elsewhere | **CodeQL only** — tests the engine-depth difference |
| SAST-11 | preview echoes `?highlight=` into HTML unescaped | **CodeQL only** `py/reflective-xss` (no ARVE Python XSS rule) |
| SEC-01 | JWT signing key in config | Gitleaks + Semgrep `hardcoded-jwt-secret` (C) |
| SEC-02 | AWS key pair in config | Gitleaks + Semgrep `upstream.python.aws-secret-key` (C) |
| SEC-03 | hardcoded DB password | Semgrep `hardcoded-password` (+ Gitleaks if it matches — record what happens) |
| SEC-04 | RSA private key `.pem` | Gitleaks |
| SEC-05 | secret added then deleted | Gitleaks, **history only** |
| SEC-06 | Slack webhook in `docs/runbook.md` | Gitleaks |
| DEP-01…04 | 4 pinned vulnerable PyPI packages (verified on osv.dev) | OSV |
| SAFE-01…04 | parameterized query, `subprocess` list args, `yaml.safe_load`, `sha256` | none |

### 5.2 JS / TS — `arve-testbed-js` (~17 plants + 3 controls)

Server code is `.ts`, the static page is `.js`. ARVE's JS rules declare both
languages, so each extension must produce findings — if only `.js` fires,
ARVE (or the rulepack) has a TypeScript gap.

| ID | Plant | Expected engines |
|---|---|---|
| SAST-01 | template-literal SQL from `req.query` (`.ts`) | Semgrep `javascript.sql-injection`, CodeQL `js/sql-injection` |
| SAST-02 | `child_process.exec` with request input (`.ts`) | Semgrep `javascript.command-injection`, CodeQL `js/command-line-injection` |
| SAST-03 | `res.send` of `req.query` (preview, `.ts`) | Semgrep `javascript.xss`, CodeQL `js/reflected-xss` |
| SAST-04 | `innerHTML` in the static page (`.js`) | Semgrep `javascript.xss` |
| SAST-05 | `eval` on settings bundle | Semgrep `upstream.javascript.eval-injection`, CodeQL `js/code-injection` |
| SAST-06 | `fs.readFile(path.join(dir, name))` | **CodeQL only** `js/path-injection` (no ARVE JS rule) |
| SAST-07 | `fetch(userUrl)` | **CodeQL only** `js/request-forgery` |
| SEC-01…06 | JWT (C w/ Semgrep), private key in `.js` (C w/ Semgrep), Stripe in `.env.example`, GitHub token in workflow, history-only, Slack in docs | Gitleaks (+Semgrep where C) |
| DEP-01…04 | 4 npm packages, incl. one **transitive** only | OSV |
| SAFE-01…03 | prepared statement, `execFile` with args, `textContent` | none |

### 5.3 Java — `arve-testbed-java` (~17 plants + 3 controls)

All SAST here is **CodeQL-only** (no ARVE Java Semgrep rules).

| ID | Plant | Expected engines |
|---|---|---|
| SAST-01 | concatenated SQL in `Statement.executeQuery` from `@RequestParam` | CodeQL `java/sql-injection` |
| SAST-02 | `ProcessBuilder("sh","-c", input)` | CodeQL `java/command-line-injection` |
| SAST-03 | `new File(dir, name)` read and returned | CodeQL `java/path-injection` |
| SAST-04 | `new URL(userUrl).openStream()` | CodeQL `java/ssrf` |
| SAST-05 | `ObjectInputStream.readObject` on uploaded bundle | CodeQL `java/unsafe-deserialization` |
| SAST-06 | controller writes request param into an HTML response | CodeQL `java/xss` |
| SAST-07 | trust-all `X509TrustManager` for the import client | CodeQL `java/insecure-trustmanager` |
| SAST-08 | `Cipher.getInstance("DES")` for share links | CodeQL `java/weak-cryptographic-algorithm` |
| SEC-01…05 | secret in `application.properties`, `.pem`, workflow AWS, history-only, Slack in docs | Gitleaks |
| DEP-01…04 | 4 Maven deps in `pom.xml`, one transitive if OSV v1.9.2 resolves transitives (see below) | OSV |
| SAFE-01…03 | `PreparedStatement`, `ProcessBuilder` with arg list and no shell, `ObjectInputFilter` allowlist | none |
| — | Semgrep | expected to run, succeed, **0 findings** |

**Java gotchas — both must be settled in P0, before any code:**

1. **CodeQL build mode.** Java needs either a build or `--build-mode=none`. ARVE's
   sandbox runs with no network, so if its CodeQL wrapper uses autobuild, Maven
   can't fetch dependencies and database creation fails. Check
   `../ARVE/docker/codeql` and the engine command. If it's autobuild-only, flag it
   to the team — that's an ARVE bug the testbed has found before it's even built.
2. **OSV on `pom.xml`.** Whether `pom.xml` transitive dependencies get resolved
   depends on the OSV version and network. Run v1.9.2 against a test `pom.xml`
   first. If it only reports direct deps, make all four `DEP-*` direct and note why.
3. **Noise floor.** Spring Boot pulls in a large tree. The P1 clean-skeleton scan
   must show 0 OSV records on a current Spring Boot release; if it doesn't, pick
   a release that does rather than documenting noise.

### 5.4 PHP — `arve-testbed-php` (~13 plants + 3 controls)

| ID | Plant | Expected engines |
|---|---|---|
| SAST-01 | concatenated SQL in `$db->query()` | Semgrep `php.sql-injection` |
| SAST-02 | `shell_exec` / `system` with request input | Semgrep `php.command-injection` |
| SAST-03 | `eval` on settings bundle | Semgrep `php.eval-injection` |
| SAST-04 | `file_get_contents($dir . $_GET['name'])` | Semgrep `php.path-traversal` |
| SEC-01…05 | config secret, `.pem`, workflow token, history-only, Slack in docs | Gitleaks |
| DEP-01…04 | 4 Composer packages in `composer.lock` | OSV |
| SAFE-01…03 | prepared statement, `escapeshellarg`, `basename` + allowlist | none |
| — | CodeQL | expected **skipped**, scan still `COMPLETED` |

---

## 6. Sessions, phases, and the review loop

### 6.1 Two usage windows for four repos

Claude plan usage runs in 5-hour windows, and **Claude Code and the Claude app
share the same pool** — every review message in the app spends the same budget
Claude Code does. So the budget is planned per window:

| Window | Work | Ends with |
|---|---|---|
| **A** | `arve-testbed-python`, all phases, pushed | team gate — happens offline, between windows |
| **B** | `js` → `php` → `java`, `/clear` between repos | three repos pushed |

Window B is the tight one. It only fits because the ports reuse everything repo 1
settled. If B runs short, **Java slips** — that's why it's last. Every phase ends
in a commit, so stopping at a phase boundary and resuming in the next window
loses nothing. Run `/status` at the start and after each phase to see where the
window stands.

### 6.2 Phases (three per repo)

| Phase | Does | Stops? |
|---|---|---|
| **P0 Verify** | read the named rule files, pick dep versions verified on osv.dev, settle language gotchas — **no code** | Python & Java: always. JS & PHP: only if something deviates from this plan |
| **P1 Build & plant** | clean skeleton → all 4 scanners = **0 findings** → plant in **three batches** (SAST, SEC, DEP), one scanner run per batch, JSON entry written as each plant goes in | yes |
| **P2 Finalize** | `seed_history.py`, render answer key, commit `baselines/`, README, push | yes (final) |

Batching instead of the ledger's scan-after-every-plant: CodeQL takes minutes
per run and every run's output costs tokens. When a batch has a miss, only that
plant gets debugged.

### 6.3 Phase report → Claude app review

Every phase ends with this block and nothing else, so it can be pasted straight
into the app:

```
=== PHASE REPORT: <repo> P<n> ===
commit: <short hash>
done: <one line>
plants: <ID> <engine> PASS|FAIL   (one per line, FAILs first; omit in P0)
deviations from plan.md: <none | list>
decisions I made: <none | list>
needs your call: <none | list>
next: <one line>
```

How the review loop runs:

- **One app chat per repo** in the ARVE Project — not one per phase — so context
  carries over without re-explaining.
- **Paste the phase report only** — not logs, not code. If the app needs a
  specific file, paste just that file.
- **Python: review after every phase** (it's the template). **Ports: review the
  final report**, plus P0 if it stopped, plus anything that FAILed.
- Bring changes back to Claude Code as a short instruction. If a change touches
  §4 conventions, it goes into `TESTBED_SPEC.md` in repo 1 first so the ports
  inherit it.

---

## 7. Token budget rules

1. **Sonnet for the build** (`/model sonnet`). Switch to Opus only to unstick a
   specific problem, then switch back.
2. **Read sections, not documents.** Each prompt names the exact `plan.md`
   sections and ARVE rule files to open. Nothing else in `../ARVE` gets read.
3. **Port, don't redesign.** Ports read the template's `TESTBED_SPEC.md`,
   `scripts/` and `expected-findings.json` — not its app code, unless stuck.
4. **Generate, don't hand-write.** Line numbers from markers; MD answer key and
   README table from JSON.
5. **Batch scanner runs; output stays on disk.** `verify_plants.py` prints one
   line per plant. Raw JSON/SARIF is never pasted into the chat — only opened to
   debug a specific FAIL.
6. **Quiet tools.** `pip -q`, `npm --silent`, `mvn -q`, `composer -q`; long logs
   go to files and get tailed only on failure.
7. **`/clear` between repos**, `/compact` if one repo's context grows long.
   `/clear` doesn't reset usage — it stops old context being resent every turn,
   which is where long sessions burn tokens.
8. **Don't run the apps.** Scanning doesn't need them. Build checks only:
   Python import, `tsc --noEmit`, `php -l`, `mvn -q package`.
9. **Small app, one history-only secret per repo.**
10. **Replies are phase reports.** No narration between steps.
11. **Do setup by hand** (§8.2). Installs and Docker image builds cost window
    time but need no AI.

---

## 8. Workspace, prerequisites, and local scanning

### 8.1 Directory layout

```
C:\projects\
├── ARVE\                   main repo — read-only reference, never modified by testbed work
├── arve-ledger-testbed\    existing — conventions reference
├── arve-testbed-python\    window A — plan.md lives here, committed
├── arve-testbed-js\        window B
├── arve-testbed-php\       window B
└── arve-testbed-java\      window B
```

Siblings, each its **own Git repo**. Never inside `ARVE\`:

- ARVE's history would permanently carry fake secrets and vulnerable lockfiles,
  and its own Gitleaks/OSV runs and GitHub push protection would fire on them.
- `seed_history.py` rewrites history — it needs a repo of its own.
- Each testbed pushes to its own GitHub remote anyway.

`plan.md` is committed in `arve-testbed-python` so the team can read it on GitHub;
the ports reference it at `../arve-testbed-python/plan.md`. Create only
`arve-testbed-python\` now; the other three are created at the start of window B.

### 8.2 Prerequisites — do these by hand before window A

- Docker Desktop running
- `gh auth status` → logged in as `ShashwatNarayan`
- Python 3.12 (window A); Node 20+, PHP 8 + Composer, JDK 17+ + Maven (window B)
- Pull the ARVE-pinned images: `semgrep/semgrep:1.90.0`,
  `ghcr.io/google/osv-scanner:v1.9.2`, `ghcr.io/gitleaks/gitleaks:v8.24.2`
- Build `arve-codeql:2.27.1` from `ARVE\docker\codeql\Dockerfile`, following
  `ARVE\docs\HANDOVER_CODEQL_AND_SECURITY_ENGINES.md` for the exact command. It's
  slow — do it once, in advance, outside Claude.

### 8.3 Scanning

`scripts/verify_plants.py` runs all four tools in Docker at ARVE's pinned
versions. It's Python rather than bash because Docker volume paths break under
Git Bash on Windows. Semgrep must run with **ARVE's rulepack**
(`../ARVE/backend/app/security/semgrep/rules`), never `--config auto` — the
registry rules are different and would make the baseline meaningless.

---

## 9. GitHub

| Repo | Remote |
|---|---|
| 1 | `ShashwatNarayan/arve-testbed-python` |
| 2 | `ShashwatNarayan/arve-testbed-js` |
| 3 | `ShashwatNarayan/arve-testbed-php` |
| 4 | `ShashwatNarayan/arve-testbed-java` |

- Create **private**: `gh repo create ShashwatNarayan/arve-testbed-<lang> --private --source . --push`.
  Public repos get GitHub push protection by default, which will block the
  push on correctly-shaped synthetic keys.
- Turn off Dependabot alerts/PRs on all four — vulnerable deps are the point, and
  an auto-merged Dependabot PR would silently destroy a `DEP-*` plant.
- Give ARVE's GitHub App access to all four so the team can scan them from ARVE.

---

## 10. Deferred / out of scope

| Item | Why deferred |
|---|---|
| Go testbed | ARVE has Go Semgrep rules + CodeQL, but not in the team's four — easy fifth later since the template ports cleanly |
| Java Semgrep rules | Belongs in the ARVE rulepack, not the testbed. Once added, the Java answer key gains Semgrep expectations |
| DAST plants (ZAP / Nuclei) | DAST isn't wired into ARVE yet |
| Running the apps in CI | Not needed for scanning; adds time and tokens |
| Rich Git-history matrix | Covered by `arve-ledger-testbed` |
| Automated ARVE-vs-answer-key scoring script | Worth doing, but on the ARVE side, after repo 1 is approved |

---

## 11. Kickstart prompts

Open Claude Code **inside** the target repo folder. Before each prompt: `/clear`
(fresh context), `/model sonnet`, `/status` (check the window).

### Prompt 1 — `arve-testbed-python` · window A (the template)

```text
WINDOW A. This whole repo must finish inside one usage window, so be terse:
every phase ends with the phase report from plan.md §6.3 and nothing else. No
narration between steps.

Read only these sections of plan.md (in this directory): §1, §2, §4, §5.1, §6,
§7, §8. ../ARVE is ARVE's main repo — read-only, never modify it.
../arve-ledger-testbed is the previous testbed: reuse its conventions and its
seed_history.py approach instead of re-deriving them.

Build arve-testbed-python: the DocVault app (§2) in Flask + sqlite3 with the
plant matrix in §5.1. This repo is also the TEMPLATE for the JS/TS, PHP and Java
testbeds, so TESTBED_SPEC.md, scripts/verify_plants.py,
scripts/render_answer_key.py, scripts/seed_history.py and the
expected-findings.json schema must be language-neutral wherever possible.

Rules that override your instincts:
1. Trivially simple app: 7 endpoints, ~12 files, SQLite, no auth.
2. Only plant what ARVE detects. For Semgrep, open only:
   ../ARVE/backend/app/security/semgrep/rulepack-manifest.json and the python,
   generic, upstream and arve/taint rule files under .../semgrep/rules/.
   Every SAST plant maps to a real ARVE rule ID or a CodeQL security-extended query.
3. Never obfuscate. Difficulty comes from location, cross-file flow (SAST-10)
   and cross-engine overlap.
4. Markers are ID-only: `# TESTBED SAST-03` on the line above the plant.
5. expected-findings.json is the only hand-edited answer key; write each entry
   as you plant. The MD answer key and README table are generated.
6. Credentials per §4.4. No secret value in any .md file.
7. ARVE-pinned scanner versions (confirm in ../ARVE/backend/app/core/config.py)
   and ARVE's own Semgrep rulepack — never `--config auto`.

Budget rules (§7): quiet installs, long logs to files, never paste scanner
JSON/SARIF into the chat, don't run the app (import check only).

Phases (§6.2) — STOP after each with a phase report:
  P0 Verify: no code. The 4 PyPI versions for DEP-01..04, each verified live
     on osv.dev (re-check affected ranges), and any §5.1 plant you expect not
     to fire, with the reason.
  P1 Build & plant: clean skeleton + scripts, all 4 scanners = 0 findings, then
     plant in three batches (SAST, SEC, DEP), one scanner run per batch. Debug
     only the plants that FAIL.
  P2 Finalize: seed_history.py (ordinary commit messages), render the answer
     key, commit baselines/, README (prominent intentional-vulnerability
     warning, synthetic-credentials statement, how to scan and score), commit
     plan.md, then
     `gh repo create ShashwatNarayan/arve-testbed-python --private --source . --push`.

Start with P0.
```

### Prompt 2 — `arve-testbed-js` · window B, repo 1 of 3

```text
WINDOW B, repo 1 of 3. JS/TS, PHP and Java must all fit in one usage window, so
be terse: phases end with the phase report from
../arve-testbed-python/plan.md §6.3 and nothing else.

Read only: ../arve-testbed-python/plan.md §4, §5.2, §6, §7, §8.3, plus the
template's TESTBED_SPEC.md, scripts/ and expected-findings.json. Do not read the
template's app code unless you are stuck. ../ARVE is read-only.

Port the approved template to an Express server in TypeScript (run with tsx) +
better-sqlite3, plus one static page in plain JS. Plant matrix: §5.2. Copy
TESTBED_SPEC.md and scripts/ unchanged except for language-specific bits
(marker `// TESTBED SAST-01`, lockfile path, CodeQL language).

For Semgrep, open only the javascript/typescript rules under
../ARVE/backend/app/security/semgrep/rules. Split plants across .ts and .js as
§5.2 says; if a rule fires on .js but not .ts, report it — that's a finding about
ARVE, don't work around it. SAST-06/07 are CodeQL-only; confirm Semgrep stays
silent. DEP-04 must be transitive-only.

Phases per §6.2. P0: continue straight into P1 unless something deviates from
the plan — then stop and report. STOP after P1 and after P2. Build check is
`tsc --noEmit`; don't run the server. Push at P2 to
ShashwatNarayan/arve-testbed-js (private). Start with P0.
```

### Prompt 3 — `arve-testbed-php` · window B, repo 2 of 3

```text
WINDOW B, repo 2 of 3 — budget is tight, be terse: phase reports only
(../arve-testbed-python/plan.md §6.3).

Read only: ../arve-testbed-python/plan.md §4, §5.4, §6, §7, §8.3, plus the
template's TESTBED_SPEC.md, scripts/ and expected-findings.json. Not the
template's app code unless stuck. ../ARVE is read-only.

Port the template to plain PHP 8 + PDO SQLite + Composer, no framework. Plant
matrix: §5.4. Copy TESTBED_SPEC.md and scripts/, changing only language-specific
bits (marker `// TESTBED SAST-01`, composer.lock, no CodeQL).

For Semgrep, open only ../ARVE/backend/app/security/semgrep/rules/php.yml and
match its exact call shapes (e.g. `$db->query()`). CodeQL doesn't support PHP:
set engine_expectations.codeql = "skipped" and document that the correct ARVE
outcome is a COMPLETED scan with CodeQL skipped — not PARTIAL, not FAILED.

Phases per §6.2. P0: continue straight into P1 unless something deviates — then
stop. STOP after P1 and after P2. Build check is `php -l`; don't run the app.
Push at P2 to ShashwatNarayan/arve-testbed-php (private). Start with P0.
```

### Prompt 4 — `arve-testbed-java` · window B, repo 3 of 3

```text
WINDOW B, repo 3 of 3 — budget is tight, be terse: phase reports only
(../arve-testbed-python/plan.md §6.3). If the window runs out mid-phase, commit
what's done and say exactly where to resume.

Read only: ../arve-testbed-python/plan.md §4, §5.3, §6, §7, §8.3, plus the
template's TESTBED_SPEC.md, scripts/ and expected-findings.json. Not the
template's app code unless stuck. ../ARVE is read-only.

Port the template to Java: Spring Boot (web starter only) + plain JDBC +
sqlite-jdbc, Maven. Plant matrix: §5.3. Copy TESTBED_SPEC.md and scripts/,
changing only language-specific bits (marker `// TESTBED SAST-01`, pom.xml,
CodeQL language). ARVE has no Java Semgrep rules, so every SAST plant is
CodeQL-only: set engine_expectations.semgrep = "no applicable rules" and
document that the correct ARVE outcome is Semgrep SUCCESS with 0 findings.

P0 always STOPS for Java. Settle the three gotchas in §5.3 and report:
  1. How ARVE's CodeQL setup (../ARVE/docker/codeql + the codeql engine) builds
     Java — build-mode none or autobuild — and whether it works with the
     sandbox network disabled. If it can't, stop: that's an ARVE bug for the
     team, not something to work around here.
  2. Whether osv-scanner v1.9.2 resolves transitive deps from pom.xml (test on a
     scratch pom.xml). If not, all DEP plants are direct.
  3. A current Spring Boot release whose clean tree gives 0 OSV records.
  Plus the 4 Maven versions for DEP-01..04, verified live on osv.dev.

STOP after P1 and after P2. Build check is `mvn -q package`; don't run the app.
Push at P2 to ShashwatNarayan/arve-testbed-java (private). Start with P0.
```
