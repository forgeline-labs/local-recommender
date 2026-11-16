"""Shared fixtures for the public black-box test suite."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


@pytest.fixture
def run_app():
    """Run the CLI through a fresh subprocess using the current interpreter."""

    def _run(*args, cwd=None, env=None):
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        if env:
            environment.update(env)
        return subprocess.run(
            [sys.executable, str(APP), *map(str, args)],
            capture_output=True,
            cwd=str(cwd) if cwd is not None else str(ROOT),
            env=environment,
        )

    return _run


@pytest.fixture
def write_interactions(tmp_path):
    """Write interactions as UTF-8 JSON and return the file path."""

    def _write(interactions, name="interactions.json"):
        path = tmp_path / name
        path.write_text(json.dumps(interactions), encoding="utf-8")
        return path

    return _write


def parse_stdout(process):
    """Parse one line of JSON stdout, asserting the LF/one-line convention."""
    assert process.stderr == b""
    assert process.stdout.endswith(b"\n")
    assert process.stdout.count(b"\n") == 1
    return json.loads(process.stdout.decode("utf-8"))
