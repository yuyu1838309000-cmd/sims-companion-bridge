"""Read-only preflight gate for a TS4Script game-test candidate."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = ROOT / "game-mod" / "dist" / "SimsCompanionBridge.ts4script"
GAME_PROCESS_NAMES = ("TS4_x64.exe", "TS4_DX9_x64.exe")
SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", "dist", "build", ".local"}
TEXT_SUFFIXES = {".py", ".js", ".html", ".css", ".json", ".toml", ".md", ".yml", ".yaml", ".txt"}
GENERIC_PATTERNS = (
    ("API-key-looking token", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("Windows user-profile path", re.compile(r"[A-Za-z]:\\Users\\[^\s\"']+")),
    ("Unix home path", re.compile(r"/home/[A-Za-z0-9._-]+/")),
)


class Report:
    def __init__(self):
        self.failures = 0
        self.blockers = 0

    def pass_(self, message):
        print("[PASS] " + message)

    def info(self, message):
        print("[INFO] " + message)

    def fail(self, message):
        self.failures += 1
        print("[FAIL] " + message)

    def block(self, message):
        self.blockers += 1
        print("[BLOCKED] " + message)


def _run(command):
    return subprocess.run(
        command,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_fingerprint():
    digest = hashlib.sha256()
    sources = [ROOT / "game-mod" / "build_ts4script.py"]
    sources.extend(sorted((ROOT / "game-mod" / "src").rglob("*.py")))
    for source in sorted(sources, key=lambda item: item.as_posix()):
        relative = source.relative_to(ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_deny_terms(path):
    if path is None:
        return []
    terms = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            terms.append(value)
    return terms


def _iter_text_files():
    for base, dirs, files in os.walk(str(ROOT)):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in files:
            candidate = Path(base) / name
            if candidate.suffix.lower() in TEXT_SUFFIXES:
                yield candidate


def check_source_scan(report, deny_terms):
    hits = []
    for path in _iter_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = str(path.relative_to(ROOT))
        for label, pattern in GENERIC_PATTERNS:
            if pattern.search(text):
                hits.append("%s: %s" % (relative, label))
        for term in deny_terms:
            if term in text:
                hits.append("%s: private deny term" % relative)
    if hits:
        for hit in hits[:20]:
            report.fail("privacy scan: " + hit)
        if len(hits) > 20:
            report.fail("privacy scan: %s additional hits" % (len(hits) - 20))
    else:
        report.pass_("public source privacy scan")


def check_git(report):
    diff = _run(["git", "diff", "--check"])
    if diff.returncode == 0:
        report.pass_("git diff --check")
    else:
        report.fail("git diff --check\n" + diff.stdout.strip())
    status = _run(["git", "status", "--porcelain"])

    if status.returncode != 0:
        report.fail("git status unavailable")
    elif status.stdout.strip():
        count = len(status.stdout.splitlines())
        report.info("working tree is dirty (%s entries); treat it as protected" % count)
    else:
        report.info("working tree is clean")


def check_tests(report, skip):
    if skip:
        report.info("pytest skipped by request")
        return
    result = _run([sys.executable, "-m", "pytest", "-q"])
    if result.returncode == 0:
        summary = result.stdout.strip().splitlines()
        report.pass_("pytest: " + (summary[-1] if summary else "passed"))
    else:
        report.fail("pytest failed\n" + result.stdout.strip())


def check_candidate(report, candidate, expected_game_version, deny_terms):
    if not candidate.is_file():
        report.block("candidate missing: %s" % candidate)
        return
    manifest_path = candidate.with_suffix(".manifest.json")
    if not manifest_path.is_file():
        report.fail("build manifest missing: %s" % manifest_path)
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        report.fail("invalid build manifest: %s" % exc)
        return

    try:
        with zipfile.ZipFile(str(candidate), "r") as archive:
            names = sorted(archive.namelist())
            pyc_names = [name for name in names if name.endswith(".pyc")]
            py_names = [name for name in names if name.endswith(".py")]
            magic_values = {archive.read(name)[:4].hex() for name in pyc_names}
            raw = b"".join(archive.read(name) for name in pyc_names)
    except (OSError, zipfile.BadZipFile) as exc:
        report.fail("invalid TS4Script archive: %s" % exc)
        return
    if not pyc_names or py_names:
        report.fail("archive must contain pyc modules and zero .py sources")
    else:
        report.pass_("archive layout: %s pyc, 0 py" % len(pyc_names))
    if len(magic_values) == 1:
        magic = next(iter(magic_values))
        report.pass_("single Python bytecode magic: %s" % magic)
    else:
        magic = None
        report.fail("archive contains mixed/missing bytecode magic")
    if re.search(br"[A-Za-z]:\\", raw) or b"/home/" in raw:
        report.fail("candidate bytecode contains an absolute filesystem path")
    else:
        report.pass_("candidate bytecode has no obvious absolute path")
    binary_private_hits = 0
    for term in deny_terms:
        if term.encode("utf-8") in raw or term.encode("utf-16le") in raw:
            binary_private_hits += 1
    if binary_private_hits:
        report.fail("candidate bytecode contains %s private deny-list hit(s)" % binary_private_hits)
    elif deny_terms:
        report.pass_("candidate bytecode private deny-list scan")
    digest = _sha256(candidate)
    checks = {
        "artifact": candidate.name,
        "artifact_sha256": digest,
        "artifact_size_bytes": candidate.stat().st_size,
        "modules": pyc_names,
        "python_magic": magic,
        "source_fingerprint": _source_fingerprint(),
        "game_version_target": expected_game_version,
        "status": "INSTALLABLE_CANDIDATE",
        "game_tested": False,
        "actions_enabled": False,
        "automatic_polling": False,
    }

    mismatches = []
    for key, expected in checks.items():
        if manifest.get(key) != expected:
            mismatches.append("%s=%r (expected %r)" % (key, manifest.get(key), expected))
    if mismatches:
        for mismatch in mismatches:
            report.fail("manifest mismatch: " + mismatch)
    else:
        report.pass_("build manifest matches candidate")
    report.info("candidate SHA256=" + digest)


def _running_game_process_names(tasklist_output):
    lowered = tasklist_output.lower()
    return [name for name in GAME_PROCESS_NAMES if name.lower() in lowered]


def check_game_process(report, skip):
    if skip:
        report.info("game-process check skipped by request")
        return
    if os.name != "nt":
        report.info("game-process check not applicable on this OS")
        return
    result = subprocess.run(
        ["tasklist", "/NH"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    if result.returncode != 0:
        report.block("could not determine whether The Sims 4 is running")
        return
    running = _running_game_process_names(result.stdout)
    if running:
        report.block("The Sims 4 is running (%s); stop before changing Live Mods" %
                     ", ".join(running))
    else:
        report.pass_("The Sims 4 is not running")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check whether a candidate is ready for the game-test gate")
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--game-version", required=True,
                        help="exact The Sims 4 version being prepared for testing")
    parser.add_argument("--deny-file", type=Path)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-game-process-check", action="store_true")
    args = parser.parse_args(argv)

    report = Report()
    deny_terms = _load_deny_terms(args.deny_file)
    check_git(report)
    check_tests(report, args.skip_tests)
    check_source_scan(report, deny_terms)
    check_candidate(report, args.candidate.resolve(), args.game_version, deny_terms)
    check_game_process(report, args.skip_game_process_check)

    if report.failures:
        print("GATE=NOT_READY")
        return 1
    if report.blockers:
        print("GATE=BLOCKED")
        return 2
    print("GATE=READY_FOR_GAME_TEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
