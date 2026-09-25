"""Build the read-only game bridge as a sourceless .ts4script archive.

Run this script with CPython 3.7, matching The Sims 4 script runtime used by
the current compatibility target. The output is a candidate only until it is
validated in game.
"""
from __future__ import absolute_import

import argparse
import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
import zipfile


ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(ROOT)
SRC = os.path.join(ROOT, "src")
DEFAULT_OUT = os.path.join(ROOT, "dist", "SimsCompanionBridge.ts4script")


def _compile_tree(temp):
    compiled = []
    for base, dirs, files in os.walk(SRC):
        dirs.sort()
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            source = os.path.join(base, name)
            relative = os.path.relpath(source, SRC)
            archive_name = os.path.splitext(relative)[0] + ".pyc"
            destination = os.path.join(temp, archive_name)
            directory = os.path.dirname(destination)
            if directory and not os.path.isdir(directory):
                os.makedirs(directory)
            py_compile.compile(
                source,
                cfile=destination,
                dfile=relative.replace(os.sep, "/"),
                doraise=True,
                invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
            )
            with open(destination, "rb") as handle:
                bytecode = handle.read()
            if source.encode("utf-8") in bytecode:
                raise RuntimeError("compiled bytecode leaked an absolute source path")
            compiled.append((destination, archive_name.replace(os.sep, "/")))
    return sorted(compiled, key=lambda item: item[1])


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_fingerprint():
    digest = hashlib.sha256()
    sources = [os.path.abspath(__file__)]
    for base, _dirs, files in os.walk(SRC):
        for name in sorted(files):
            if name.endswith(".py"):
                sources.append(os.path.join(base, name))
    for source in sorted(sources):
        relative = os.path.relpath(source, REPO_ROOT).replace(os.sep, "/")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        with open(source, "rb") as handle:
            digest.update(handle.read())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_state():
    try:
        head = subprocess.check_output(
            ["git", "-C", REPO_ROOT, "rev-parse", "HEAD"],
            universal_newlines=True,
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", REPO_ROOT, "status", "--porcelain"],
            universal_newlines=True,
        )
        return {"head": head, "dirty": bool(status.strip())}
    except (OSError, subprocess.CalledProcessError):
        return {"head": None, "dirty": None}


def main(argv=None):
    if sys.version_info[:2] != (3, 7):
        raise RuntimeError("build_ts4script.py must run under CPython 3.7")
    parser = argparse.ArgumentParser(description="Build Sims Companion Bridge TS4Script")
    parser.add_argument("--output", default=DEFAULT_OUT)
    parser.add_argument("--game-version", required=True,
                        help="exact The Sims 4 version this candidate targets")
    args = parser.parse_args(argv)
    output = os.path.abspath(args.output)
    output_dir = os.path.dirname(output)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    temp = tempfile.mkdtemp(prefix="scb-ts4script-")
    try:
        compiled = _compile_tree(temp)
        if not compiled:
            raise RuntimeError("no game-mod Python sources found")
        if os.path.exists(output):
            os.remove(output)
        with zipfile.ZipFile(output, "w") as archive:
            for disk_path, archive_path in compiled:
                info = zipfile.ZipInfo(archive_path, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with open(disk_path, "rb") as handle:
                    archive.writestr(info, handle.read())
        with open(compiled[0][0], "rb") as handle:
            magic = handle.read(4).hex()
        manifest_path = os.path.splitext(output)[0] + ".manifest.json"
        manifest = {
            "schema_version": 1,
            "status": "INSTALLABLE_CANDIDATE",
            "game_tested": False,
            "game_version_target": args.game_version,
            "artifact": os.path.basename(output),
            "artifact_sha256": _sha256(output),
            "artifact_size_bytes": os.path.getsize(output),
            "python_version": "%s.%s.%s" % sys.version_info[:3],
            "python_magic": magic,
            "modules": [item[1] for item in compiled],
            "source_fingerprint": _source_fingerprint(),
            "actions_enabled": False,
            "automatic_polling": False,
            "git": _git_state(),
        }
        with open(manifest_path, "w") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print("BUILT=%s" % output)
        print("MANIFEST=%s" % manifest_path)
        print("SHA256=%s" % manifest["artifact_sha256"])
        print("FILES=%s" % len(compiled))
        print("PYTHON=%s" % manifest["python_version"])
        print("MAGIC=%s" % magic)
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
