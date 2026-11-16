"""Black-box tests for the ``app`` command-line interface.

The CLI is always exercised through a subprocess with ``sys.executable`` so the
same suite runs on Windows and POSIX.
"""

import json
import os
import stat
import sys

import pytest
from conftest import APP, ROOT, parse_stdout

EXAMPLE = [
    {"user": "u1", "item": "a"},
    {"user": "u2", "item": "a"},
    {"user": "u2", "item": "b"},
]


def test_version_is_exact(run_app):
    process = run_app("--version")
    assert process.returncode == 0
    assert process.stdout == b"local-recommender 0.1.0\n"
    assert process.stderr == b""


def test_help_documents_commands_and_options(run_app):
    process = run_app("--help")
    assert process.returncode == 0
    assert process.stderr == b""
    text = process.stdout.decode("utf-8")
    for token in (
        "usage:",
        "app",
        "--help",
        "--version",
        "recommend",
        "--user",
        "--limit",
        "FILE",
    ):
        assert token in text


def test_ac1_example_through_cli(run_app, write_interactions):
    path = write_interactions(EXAMPLE)
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 0
    assert parse_stdout(process) == [{"item": "b", "score": 0.707107}]


def test_ac1_limit_option_through_cli(run_app, write_interactions):
    interactions = EXAMPLE + [{"user": "u2", "item": "c"}]
    path = write_interactions(interactions)
    process = run_app("recommend", path, "--user", "u1", "--limit", "1")
    assert process.returncode == 0
    result = parse_stdout(process)
    assert len(result) == 1
    assert result[0]["item"] == "b"


def test_ac2_unknown_user_through_cli(run_app, write_interactions):
    path = write_interactions(EXAMPLE)
    process = run_app("recommend", path, "--user", "nobody")
    assert process.returncode == 0
    assert process.stdout == b"[]\n"
    assert process.stderr == b""


def test_ac2_empty_array_through_cli(run_app, tmp_path):
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 0
    assert process.stdout == b"[]\n"


def test_ac4_duplicate_pairs_through_cli(run_app, write_interactions):
    single = write_interactions(EXAMPLE, "single.json")
    duplicated = write_interactions(EXAMPLE * 3, "duplicated.json")
    first = run_app("recommend", single, "--user", "u1")
    second = run_app("recommend", duplicated, "--user", "u1")
    assert parse_stdout(first) == parse_stdout(second)


@pytest.mark.parametrize("limit", ["0", "101", "-1", "true", "1.5", "abc", ""])
def test_ac6_invalid_limit_through_cli(run_app, write_interactions, limit):
    path = write_interactions(EXAMPLE)
    process = run_app("recommend", path, "--user", "u1", "--limit", limit)
    assert process.returncode == 2
    assert process.stdout == b""
    assert process.stderr.startswith(b"error:")
    assert process.stderr.count(b"\n") == 1


def test_ac6_limit_100_is_accepted(run_app, write_interactions):
    path = write_interactions(EXAMPLE)
    process = run_app("recommend", path, "--user", "u1", "--limit", "100")
    assert process.returncode == 0


def test_ac7_extra_field_through_cli(run_app, write_interactions):
    path = write_interactions([{"user": "u1", "item": "a", "weight": 2}])
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 2
    assert process.stdout == b""
    assert process.stderr.startswith(b"error:")


def test_ac7_missing_user_field_through_cli(run_app, write_interactions):
    path = write_interactions([{"item": "a"}])
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 2


def test_ac7_non_array_json_through_cli(run_app, write_interactions):
    path = write_interactions({"user": "u1", "item": "a"})
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 2


def test_ac7_invalid_json_through_cli(run_app, tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("[{", encoding="utf-8")
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 2
    assert process.stdout == b""


def test_ac7_duplicate_json_keys_are_rejected(run_app, tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('[{"user":"u1","user":"u2","item":"a"}]', encoding="utf-8")
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 2


@pytest.mark.parametrize("payload", [b'[{"user":"u1","item":NaN}]', b"[Infinity]"])
def test_ac7_non_finite_json_constants_are_rejected(run_app, tmp_path, payload):
    path = tmp_path / "nonfinite.json"
    path.write_bytes(payload)
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 2


def test_ac7_invalid_utf8_through_cli(run_app, tmp_path):
    path = tmp_path / "latin1.json"
    path.write_bytes(b'[{"user":"u1","item":"\xe9"}]')
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 2


def test_utf8_bom_is_rejected_as_invalid_json(run_app, tmp_path):
    path = tmp_path / "bom.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(EXAMPLE).encode("utf-8"))
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 2


def test_ac8_reordering_file_through_cli(run_app, write_interactions):
    forward = write_interactions(EXAMPLE, "forward.json")
    backward = write_interactions(list(reversed(EXAMPLE)), "backward.json")
    first = parse_stdout(run_app("recommend", forward, "--user", "u1"))
    second = parse_stdout(run_app("recommend", backward, "--user", "u1"))
    assert first == second


def test_ac11_too_many_records_through_cli(run_app, tmp_path):
    path = tmp_path / "large-array.json"
    interactions = [
        {"user": f"u{index % 100}", "item": f"i{index % 100}"} for index in range(10001)
    ]
    path.write_text(json.dumps(interactions), encoding="utf-8")
    process = run_app("recommend", path, "--user", "u0")
    assert process.returncode == 2
    assert process.stdout == b""


def test_ac11_too_many_items_through_cli(run_app, tmp_path):
    path = tmp_path / "many-items.json"
    interactions = [{"user": "u0", "item": f"i{index}"} for index in range(1001)]
    path.write_text(json.dumps(interactions), encoding="utf-8")
    process = run_app("recommend", path, "--user", "u0")
    assert process.returncode == 2


def test_ac12_missing_file_exits_three(run_app, tmp_path):
    process = run_app("recommend", tmp_path / "missing.json", "--user", "u1")
    assert process.returncode == 3
    assert process.stdout == b""
    assert process.stderr.startswith(b"error:")
    assert process.stderr.count(b"\n") == 1


def test_ac12_missing_parent_directory_exits_three(run_app, tmp_path):
    process = run_app("recommend", tmp_path / "no-such-dir" / "in.json", "--user", "u1")
    assert process.returncode == 3
    assert process.stdout == b""


def test_ac12_directory_as_input_exits_three(run_app, tmp_path):
    process = run_app("recommend", tmp_path, "--user", "u1")
    assert process.returncode == 3


def test_ac12_no_file_is_created_on_failure(run_app, tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    process = run_app("recommend", "absent.json", "--user", "u1", cwd=workdir)
    assert process.returncode == 3
    assert list(workdir.iterdir()) == []


def test_ac12_input_file_is_not_modified(run_app, write_interactions):
    path = write_interactions(EXAMPLE)
    before = path.read_bytes()
    run_app("recommend", path, "--user", "u1")
    run_app("recommend", path, "--user", "unknown")
    assert path.read_bytes() == before


def test_file_of_exactly_one_mebibyte_is_accepted(run_app, tmp_path):
    path = tmp_path / "max.json"
    payload = json.dumps(EXAMPLE).encode("utf-8")
    data = payload + b" " * (1048576 - len(payload))
    assert len(data) == 1048576
    path.write_bytes(data)
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 0
    assert parse_stdout(process) == [{"item": "b", "score": 0.707107}]


def test_file_above_one_mebibyte_is_rejected(run_app, tmp_path):
    path = tmp_path / "too-big.json"
    payload = json.dumps(EXAMPLE).encode("utf-8")
    path.write_bytes(payload + b" " * (1048576 + 1 - len(payload)))
    assert path.stat().st_size == 1048577
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 2
    assert process.stdout == b""


def test_unicode_path_and_path_with_spaces(run_app, tmp_path):
    directory = tmp_path / "datos de prueba ñandú"
    directory.mkdir()
    path = directory / "interacciones con espacios.json"
    path.write_text(json.dumps(EXAMPLE), encoding="utf-8")
    process = run_app("recommend", path, "--user", "u1")
    assert process.returncode == 0
    assert parse_stdout(process) == [{"item": "b", "score": 0.707107}]


def test_unknown_argument_exits_two(run_app):
    process = run_app("--nope")
    assert process.returncode == 2
    assert process.stdout == b""
    assert process.stderr.startswith(b"error:")


def test_missing_command_exits_two(run_app):
    process = run_app()
    assert process.returncode == 2
    assert process.stdout == b""
    assert process.stderr.startswith(b"error:")


def test_missing_required_user_exits_two(run_app, write_interactions):
    path = write_interactions(EXAMPLE)
    process = run_app("recommend", path)
    assert process.returncode == 2
    assert process.stdout == b""


def test_missing_file_argument_exits_two(run_app):
    process = run_app("recommend", "--user", "u1")
    assert process.returncode == 2


def test_invalid_target_user_exits_two(run_app, write_interactions):
    path = write_interactions(EXAMPLE)
    process = run_app("recommend", path, "--user", "not valid")
    assert process.returncode == 2
    assert process.stdout == b""


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable bit and shebang")
def test_posix_executable_entrypoint_is_equivalent(run_app):
    import subprocess

    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    process = subprocess.run(
        [str(APP), "--version"],
        capture_output=True,
        cwd=str(ROOT),
        env=environment,
    )
    assert process.returncode == 0
    assert process.stdout == b"local-recommender 0.1.0\n"
    assert process.stderr == b""


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission model")
def test_read_only_working_directory_simulation(run_app, tmp_path):
    """A write-failure environment (read-only directory) must not affect a run.

    The program never writes files, so a strictly read-only working directory
    is a portable way to prove that no unexpected output file is attempted.
    When the test user can bypass permissions (for example root), the
    directory check is still valid because the program must leave it empty.
    """
    workdir = tmp_path / "read-only"
    workdir.mkdir()
    path = tmp_path / "input.json"
    path.write_text(json.dumps(EXAMPLE), encoding="utf-8")
    original_mode = workdir.stat().st_mode
    os.chmod(workdir, stat.S_IRUSR | stat.S_IXUSR)
    try:
        writable = os.access(workdir, os.W_OK)
        process = run_app("recommend", path, "--user", "u1", cwd=workdir)
        assert process.returncode == 0
        assert parse_stdout(process) == [{"item": "b", "score": 0.707107}]
        assert list(workdir.iterdir()) == []
        if not writable:
            # Externally simulated write failure: opening a new file fails.
            with pytest.raises(OSError):
                (workdir / "probe").write_text("x", encoding="utf-8")
    finally:
        os.chmod(workdir, original_mode)


@pytest.mark.skipif(sys.platform != "win32", reason="app.cmd is Windows-only")
def test_windows_cmd_wrapper_propagates_arguments_and_exit_code(tmp_path):
    import subprocess

    directory = tmp_path / "with spaces"
    directory.mkdir()
    path = directory / "in teractions.json"
    path.write_text(json.dumps(EXAMPLE), encoding="utf-8")
    for args, expected in (
        (("--version",), 0),
        (("recommend", str(path), "--user", "u1"), 0),
        (("recommend", str(directory / "missing.json"), "--user", "u1"), 3),
        (("recommend", str(path), "--limit", "0", "--user", "u1"), 2),
    ):
        process = subprocess.run(
            ["cmd", "/c", str(ROOT / "app.cmd"), *args],
            capture_output=True,
            cwd=str(ROOT),
        )
        assert process.returncode == expected
