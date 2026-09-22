#!/usr/bin/env python3
"""Run ARVE's four engines at their pinned versions and score them against the answer key.

Language-neutral: everything repo-specific comes from expected-findings.json.

Engines (all in Docker, versions pinned to ARVE's backend/app/core/config.py):
  gitleaks     ghcr.io/gitleaks/gitleaks:v8.24.2   dir over the working tree
                                                   (+ git over history with --history)
  osv          ghcr.io/google/osv-scanner:v1.9.2   recursive lockfile scan
  semgrep      semgrep/semgrep:1.90.0              ARVE's own rulepack (never --config auto)
  codeql       arve-codeql:2.27.1                  ARVE wrapper, security-extended

The scanned tree is `git ls-files -co --exclude-standard` copied with LF endings,
so it works before the first commit and ignores .venv/, storage/ etc.

Output is one line per (finding, engine): PASS / FAIL, then any UNEXPECTED
finding not explained by the answer key. Raw reports go to .scan/ and are never
printed. Gitleaks always runs with --redact.

Usage:
    python scripts/verify_plants.py                       # all engines
    python scripts/verify_plants.py --engines semgrep,codeql
    python scripts/verify_plants.py --history             # also gitleaks over git history
    python scripts/verify_plants.py --save-baselines      # copy reports into baselines/

Environment: ARVE_RULES overrides the rulepack path
(default ../ARVE/backend/app/security/semgrep/rules).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN_DIR = REPO / ".scan"
RULES = Path(os.environ.get("ARVE_RULES", REPO.parent / "ARVE/backend/app/security/semgrep/rules")).resolve()
MANIFEST = RULES.parent / "rulepack-manifest.json"

IMAGES = {
    "gitleaks": "ghcr.io/gitleaks/gitleaks:v8.24.2",
    "osv": "ghcr.io/google/osv-scanner:v1.9.2",
    "semgrep": "semgrep/semgrep:1.90.0",
    "codeql": "arve-codeql:2.27.1",
}
REPORTS = {"gitleaks": "gitleaks.json", "gitleaks-history": "gitleaks-history.json",
           "osv": "osv.json", "semgrep": "semgrep.sarif", "codeql": "codeql.sarif"}


def docker(args, label):
    log = SCAN_DIR / f"{label}.log"
    result = subprocess.run(["docker", "run", "--rm", *args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    log.write_text(result.stdout + "\n--- stderr ---\n" + result.stderr, encoding="utf-8")
    return result


def materialise(dest):
    files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=REPO,
                           capture_output=True, text=True, check=True).stdout.splitlines()
    for rel in files:
        src = REPO / rel
        if not src.is_file():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        if b"\0" not in data:
            data = data.replace(b"\r\n", b"\n")
        target.write_bytes(data)


# ---------------------------------------------------------------- scanners

def run_gitleaks(tree, out, history=False):
    mode, mount, name = ("git", "/repo", "gitleaks-history") if history else ("dir", "/code", "gitleaks")
    src = REPO if history else tree
    docker(["--network=none", "-v", f"{src}:{mount}:ro", "-v", f"{out}:/output", IMAGES["gitleaks"],
            mode, mount, "--report-format", "json", "--report-path", f"/output/{REPORTS[name]}",
            "--redact", "--exit-code", "0"], name)
    report = out / REPORTS[name]
    if not report.exists():
        raise SystemExit(f"{name} produced no report; see .scan/{name}.log")
    return [{"engine": "gitleaks", "rule": d["RuleID"],
             "file": d["File"].replace("\\", "/").split(mount.lstrip("/") + "/", 1)[-1].lstrip("/"),
             "line": d["StartLine"], "commit": (d.get("Commit") or "")[:8]}
            for d in json.loads(report.read_text(encoding="utf-8"))]


def run_osv(tree, out):
    docker(["-v", f"{tree}:/code:ro", "-v", f"{out}:/output", IMAGES["osv"],
            "--format", "json", "--output", f"/output/{REPORTS['osv']}", "-r", "/code"], "osv")
    report = out / REPORTS["osv"]
    if not report.exists():
        raise SystemExit("osv produced no report; see .scan/osv.log")
    records = []
    for res in json.loads(report.read_text(encoding="utf-8")).get("results") or []:
        source = res["source"]["path"].replace("/code/", "")
        for pkg in res.get("packages") or []:
            for vuln in pkg.get("vulnerabilities") or []:
                records.append({"engine": "osv", "rule": vuln["id"], "file": source, "line": None,
                                "package": pkg["package"]["name"], "version": pkg["package"]["version"],
                                "aliases": vuln.get("aliases") or []})
    return records


def sarif_results(report, engine, normalise=lambda r: r):
    found = []
    for run in json.loads(report.read_text(encoding="utf-8")).get("runs") or []:
        for res in run.get("results") or []:
            loc = res["locations"][0]["physicalLocation"]
            found.append({"engine": engine, "rule": normalise(res["ruleId"]),
                          "file": loc["artifactLocation"]["uri"].replace("file:///code/", ""),
                          "line": loc["region"]["startLine"]})
    return found


def semgrep_rule_ids():
    return set(json.loads(MANIFEST.read_text(encoding="utf-8"))["rules"])


def run_semgrep(tree, out):
    known = semgrep_rule_ids()

    def normalise(rule):
        return next((k for k in known if rule == k or rule.endswith("." + k)), rule)

    docker(["--network=none", "-v", f"{tree}:/code:ro", "-v", f"{RULES}:/rules:ro",
            "-v", f"{out}:/output", "-w", "/code", IMAGES["semgrep"],
            "semgrep", "scan", "--config", "/rules", "--metrics=off", "--disable-version-check",
            "--sarif", "--output", f"/output/{REPORTS['semgrep']}", "."], "semgrep")
    report = out / REPORTS["semgrep"]
    if not report.exists():
        raise SystemExit("semgrep produced no report; see .scan/semgrep.log")
    return sarif_results(report, "semgrep", normalise)


def run_codeql(tree, out):
    # The wrapper is run through `tr -d '\r'`: an image built from a Windows checkout
    # (core.autocrlf=true) bakes CRLF into run-codeql.sh and its shebang then fails.
    # Stripping CRs is a no-op for an image built from an LF checkout.
    wrapper = "/opt/arve-codeql/run-codeql.sh"
    docker(["--network=none", "--memory=4g", "--cpus=2", "-v", f"{tree}:/code:ro",
            "-v", f"{out}:/output", "--entrypoint", "bash", IMAGES["codeql"], "-c",
            f"tr -d '\\r' < {wrapper} > /tmp/run-codeql.sh && "
            f"bash /tmp/run-codeql.sh --output /output/{REPORTS['codeql']}"], "codeql")
    report = out / REPORTS["codeql"]
    if not report.exists():
        raise SystemExit("codeql produced no report; see .scan/codeql.log")
    return sarif_results(report, "codeql")


# ---------------------------------------------------------------- scoring

def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def spot(entry, history):
    if entry.get("history_only"):
        if not history:
            return None
        h = entry["history"]
        return h["file_path"], h["line_start"], h.get("line_span", 1)
    return entry["file_path"], entry.get("line_start"), entry.get("line_span", 1)


def at(finding, file_path, line, span):
    return finding["file"] == file_path and line and line <= finding["line"] < line + span


def score(key, observed, engines, history):
    lines, fails, explained = [], 0, set()
    for entry in key["findings"]:
        loc = spot(entry, history)
        if entry["finding_type"] == "dependency":
            if "osv" not in engines:
                continue
            hits = [i for i, f in enumerate(observed) if f["engine"] == "osv"
                    and f["package"].lower() == entry["package"].lower() and f["version"] == entry["version"]]
            explained.update(hits)
            want = set(as_list(entry["rule_ids"].get("osv")))
            got = {observed[i]["rule"] for i in hits}
            ok = bool(hits) and (not want or want == got)
            detail = "" if ok or not want else f"  (missing {sorted(want - got)}, extra {sorted(got - want)})"
            lines.append((ok, f"{entry['id']:8} osv      {'PASS' if ok else 'FAIL'}  {len(got)} advisories{detail}"))
            fails += not ok
            continue
        if loc is None:
            continue
        file_path, line, span = loc
        # A working-tree gitleaks hit (no commit) can only explain a HEAD plant; a history hit
        # (with commit) explains either kind, since HEAD secrets also appear in history.
        here = [i for i, f in enumerate(observed) if f["engine"] != "osv" and at(f, file_path, line, span)
                and (f["engine"] != "gitleaks" or f.get("commit") or not entry.get("history_only"))]
        if entry["kind"] == "negative":
            bad = [observed[i] for i in here if observed[i]["engine"] in engines]
            explained.update(here)
            ok = not bad
            lines.append((ok, f"{entry['id']:8} all      {'PASS' if ok else 'FAIL'}"
                              + ("" if ok else "  " + ", ".join(f"{b['engine']}:{b['rule']}" for b in bad))))
            fails += not ok
            continue
        for engine in entry["expected_engines"]:
            if engine not in engines:
                continue
            want = as_list(entry["rule_ids"].get(engine))
            mine = [i for i in here if observed[i]["engine"] == engine]
            explained.update(mine)
            got = {observed[i]["rule"] for i in mine}
            ok = bool(mine) and all(r in got for r in want)
            extra = f"  saw {sorted(got)}" if (not ok or not want) and got else ""
            lines.append((ok, f"{entry['id']:8} {engine:8} {'PASS' if ok else 'FAIL'}{extra}"))
            fails += not ok
        # findings at a plant from engines the key does not expect are still unexpected
        for i in here:
            if observed[i]["engine"] not in entry["expected_engines"]:
                explained.discard(i)
    unexpected = [f for i, f in enumerate(observed) if i not in explained and f["engine"] in engines
                  and not (f["engine"] == "gitleaks" and f.get("commit") and not history)]
    return lines, fails, unexpected


def sanitise(report):
    """Baselines are committed and scanned like any other file, so strip every copy of
    source text: SARIF snippets/context, and gitleaks Match/Secret/Line."""
    data = json.loads(report.read_text(encoding="utf-8"))

    def scrub(node):
        if isinstance(node, dict):
            for k in ("snippet", "contextRegion"):
                node.pop(k, None)
            for k in ("Match", "Secret", "Line"):
                if k in node:
                    node[k] = "REDACTED"
            for v in node.values():
                scrub(v)
        elif isinstance(node, list):
            for v in node:
                scrub(v)
    scrub(data)
    return json.dumps(data, indent=1) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--engines", default="gitleaks,osv,semgrep,codeql")
    parser.add_argument("--history", action="store_true", help="also run gitleaks over git history")
    parser.add_argument("--save-baselines", action="store_true")
    args = parser.parse_args()
    engines = [e.strip() for e in args.engines.split(",") if e.strip()]

    key = json.loads((REPO / "expected-findings.json").read_text(encoding="utf-8"))
    SCAN_DIR.mkdir(exist_ok=True)
    out = SCAN_DIR / "reports"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()

    observed = []
    with tempfile.TemporaryDirectory(prefix="testbed-") as tmp:
        tree = Path(tmp) / "code"
        tree.mkdir()
        materialise(tree)
        runners = {"gitleaks": run_gitleaks, "osv": run_osv, "semgrep": run_semgrep, "codeql": run_codeql}
        for engine in engines:
            if key["engine_expectations"].get(engine) == "skipped":
                print(f"{engine}: skipped by engine_expectations")
                continue
            observed += runners[engine](tree, out)
        if args.history and "gitleaks" in engines:
            observed += run_gitleaks(tree, out, history=True)

    lines, fails, unexpected = score(key, observed, engines, args.history)
    for ok, text in sorted(lines, key=lambda x: x[0]):
        print(text)
    for f in unexpected:
        where = f"{f['file']}:{f['line']}" if f["line"] else f"{f['file']} {f.get('package')}=={f.get('version')}"
        print(f"UNEXPECTED {f['engine']:8} {f['rule']}  {where}" + (f" @{f['commit']}" if f.get("commit") else ""))
    counts = {e: sum(1 for f in observed if f["engine"] == e and not f.get("commit")) for e in engines}
    if args.history and "gitleaks" in engines:
        counts["gitleaks_history"] = sum(1 for f in observed if f["engine"] == "gitleaks" and f.get("commit"))
    expected_counts = key.get("expected_counts", {})
    for name, n in counts.items():
        want = expected_counts.get(name)
        if want is not None and want != n:
            print(f"COUNT      {name}: observed {n}, expected {want}")
            fails += 1
    print("totals: " + ", ".join(f"{e}={n}" for e, n in counts.items())
          + f" | fails={fails} unexpected={len(unexpected)}")

    if args.save_baselines:
        base = REPO / "baselines"
        base.mkdir(exist_ok=True)
        for report in out.iterdir():
            (base / report.name).write_text(sanitise(report), encoding="utf-8", newline="\n")
    sys.exit(1 if fails or unexpected else 0)


if __name__ == "__main__":
    main()
