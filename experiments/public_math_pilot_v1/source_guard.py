"""Verify a published execution archive and input before importing GPU code.

The expected inventory SHA is supplied independently by the deployment wrapper.
A .git directory is optional for an archive; when present its HEAD and tracked
source bytes must also match. No dependency here imports Torch or a model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SOURCE_ROOT = "experiments/public_math_pilot_v1"
PREFLIGHT_MODULE = "experiments.public_math_pilot_v1.preflight"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")


def _sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _load_unique_json(path):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("Duplicate key in frozen inventory")
            value[key] = item
        return value
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs)


def _sources(repo):
    root = repo / SOURCE_ROOT
    for parent in (repo / "experiments", root):
        if parent.is_symlink() or not parent.is_dir():
            raise ValueError("Execution source namespace is missing or symlinked")
    result = {}
    for folder, directories, files in os.walk(root, followlinks=False):
        # Bytecode caches are not source and are never inventoried/executed as
        # script entrypoints. All other subdirectories are part of the closure.
        directories[:] = [name for name in directories if name != "__pycache__"]
        if any((Path(folder) / name).is_symlink() for name in directories):
            raise ValueError("Symlinked directory inside execution source")
        for name in files:
            if not name.endswith(".py"):
                continue
            path = Path(folder) / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("Symlinked or nonregular Python source")
            result[path.relative_to(repo).as_posix()] = path
    return result


def verify_inventory(inventory_path, inputs_path, *, expected_source_commit,
                     expected_inventory_sha256, repo_root=None):
    if not isinstance(expected_source_commit, str) or not _COMMIT.fullmatch(expected_source_commit):
        raise ValueError("Expected published full commit SHA required")
    if not isinstance(expected_inventory_sha256, str) or not _SHA256.fullmatch(expected_inventory_sha256):
        raise ValueError("Independently supplied inventory SHA256 required")
    repo = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    inventory_path = Path(inventory_path)
    inputs_path = Path(inputs_path)
    for path in (inventory_path, inputs_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Inventory/input must be existing regular files")
    inventory_sha = _sha(inventory_path)
    if inventory_sha != expected_inventory_sha256:
        raise ValueError("Frozen inventory SHA differs")
    frozen = _load_unique_json(inventory_path)
    if (frozen.get("schema") != 1 or frozen.get("source_commit") != expected_source_commit
            or not isinstance(frozen.get("source_files_sha256"), dict)
            or not isinstance(frozen.get("inputs_sha256"), str)
            or not _SHA256.fullmatch(frozen["inputs_sha256"])):
        raise ValueError("Frozen inventory schema/commit/input identity differs")
    wanted = frozen["source_files_sha256"]
    if not wanted or any(not isinstance(v, str) or not _SHA256.fullmatch(v) for v in wanted.values()):
        raise ValueError("Invalid Python source hash inventory")
    actual = _sources(repo)
    if set(actual) != set(wanted):
        raise ValueError("Python source closure differs: missing=" + repr(sorted(set(wanted)-set(actual)))
                         + "; extra=" + repr(sorted(set(actual)-set(wanted))))
    for required in ("preflight.py", "source_guard.py"):
        if f"{SOURCE_ROOT}/{required}" not in actual:
            raise ValueError("Required guarded execution source is missing")
    for name, path in sorted(actual.items()):
        if _sha(path) != wanted[name]:
            raise ValueError("Frozen Python source SHA differs: " + name)
    inputs_sha = _sha(inputs_path)
    if inputs_sha != frozen["inputs_sha256"]:
        raise ValueError("Frozen preflight input SHA differs")
    git_checked = False
    if (repo / ".git").exists():
        def git(*args):
            return subprocess.check_output(["git", "-C", str(repo), *args],
                text=True, stderr=subprocess.STDOUT, timeout=30).strip()
        try:
            if git("rev-parse", "HEAD") != expected_source_commit:
                raise ValueError("Git checkout HEAD differs from published source")
            git("ls-files", "--error-unmatch", "--", *sorted(actual))
            git("diff", "--exit-code", "HEAD", "--", *sorted(actual))
        except subprocess.CalledProcessError as error:
            raise ValueError("Git execution source is untracked or changed") from error
        git_checked = True
    return dict(status="verified", source_commit=expected_source_commit,
        inventory_sha256=inventory_sha, inputs_sha256=inputs_sha,
        python_source_files=len(actual), source_root=SOURCE_ROOT,
        git_checkout_additionally_checked=git_checked,
        publication_evidence="expected commit and inventory SHA supplied by deployment wrapper")


def bound_preflight_arguments(arguments, *, inputs_path, source_commit):
    """Require a single exact input and commit; preserve all other CLI options."""
    arguments = list(arguments)
    if arguments[:1] == ["--"]:
        arguments.pop(0)
    positions = {}
    for key in ("--inputs", "--source-commit"):
        found = [i for i, value in enumerate(arguments) if value == key or value.startswith(key + "=")]
        if len(found) != 1:
            raise ValueError("Exactly one preflight " + key + " is required")
        position = found[0]
        argument = arguments[position]
        if "=" in argument:
            value = argument.split("=", 1)[1]
            positions[key] = (position, True, value)
        elif position + 1 < len(arguments) and not arguments[position + 1].startswith("--"):
            positions[key] = (position, False, arguments[position + 1])
        else:
            raise ValueError("Missing preflight option value")
    canonical_input = str(Path(inputs_path).resolve())
    if str(Path(positions["--inputs"][2]).resolve()) != canonical_input:
        raise ValueError("Executed preflight inputs differ from verified inputs")
    if positions["--source-commit"][2] != source_commit:
        raise ValueError("Executed preflight source commit differs from verified source")
    position, equals, _ = positions["--inputs"]
    if equals:
        arguments[position] = "--inputs=" + canonical_input
    else:
        arguments[position + 1] = canonical_input
    return arguments


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--expected-source-commit", required=True)
    parser.add_argument("--expected-inventory-sha256", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify-only", action="store_true")
    mode.add_argument("--exec-preflight", action="store_true")
    parser.add_argument("preflight_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    arguments = None
    if args.exec_preflight:
        arguments = bound_preflight_arguments(args.preflight_args, inputs_path=args.inputs,
                                             source_commit=args.expected_source_commit)
    elif args.preflight_args:
        raise ValueError("Verify-only mode does not accept execution arguments")
    result = verify_inventory(args.inventory, args.inputs,
        expected_source_commit=args.expected_source_commit,
        expected_inventory_sha256=args.expected_inventory_sha256)
    print(json.dumps(result, sort_keys=True), flush=True)
    if arguments is not None:
        os.chdir(Path(__file__).resolve().parents[2])
        os.execv(sys.executable, [sys.executable, "-B", "-m", PREFLIGHT_MODULE, *arguments])
    return result


if __name__ == "__main__":
    main()
