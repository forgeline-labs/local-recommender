"""Command-line interface for local-recommender.

``python app recommend FILE --user USER [--limit N]`` reads JSON
interactions and prints the recommendation list as one line of JSON.
"""

import argparse
import json
import os
import re
import sys

from .recommend import MAX_LIMIT, MIN_LIMIT, recommend

PRODUCT = "local-recommender"
VERSION = "0.1.0"
MAX_INPUT_BYTES = 1024 * 1024
_LIMIT_PATTERN = re.compile(r"[0-9]+")


class _CliError(Exception):
    """An expected command-line failure carrying an exit code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _one_line(message):
    return " ".join(str(message).splitlines()) or "unexpected error"


def _write_stream(stream, text):
    data = text.encode("utf-8", "replace")
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        buffer.write(data)
        buffer.flush()
    else:  # pragma: no cover - only non-standard streams take this path
        stream.write(text)
        stream.flush()


def _write_error(message):
    _write_stream(sys.stderr, f"error: {_one_line(message)}\n")


def _write_stdout(text):
    _write_stream(sys.stdout, text)


class _Parser(argparse.ArgumentParser):
    """Argument parser with one-line ``error:`` diagnostics and LF output."""

    def _print_message(self, message, file=None):
        if not message:
            return
        stream = sys.stdout if file is None else file
        _write_stream(stream, message)

    def error(self, message):
        self.exit(2, f"error: {_one_line(message)}\n")


def _build_parser():
    parser = _Parser(
        prog="app",
        description="Deterministic item-item collaborative recommendations.",
        epilog=(
            "commands:\n"
            "  recommend FILE --user USER [--limit N]"
            "   recommend items for a user\n"
            "options:\n"
            "  --user USER    ASCII identification string of the user\n"
            "  --limit N      maximum number of recommendations, 1..100"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PRODUCT} {VERSION}",
        help="show the product version and exit",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    recommend_parser = subparsers.add_parser(
        "recommend",
        help="recommend items for a user from a JSON interactions file",
        description=(
            'Read a JSON array of {"user": ..., "item": ...} objects and '
            "print the recommendations as a JSON array."
        ),
    )
    recommend_parser.add_argument(
        "file",
        metavar="FILE",
        help="path to a UTF-8 JSON interactions file (at most 1 MiB)",
    )
    recommend_parser.add_argument(
        "--user",
        metavar="USER",
        required=True,
        help="ASCII identification string of the user to recommend for",
    )
    recommend_parser.add_argument(
        "--limit",
        metavar="N",
        default="5",
        help="maximum number of recommendations, 1..100 (default: 5)",
    )
    return parser


def _read_input_bytes(path):
    """Read the input file, distinguishing oversized input from I/O errors."""
    try:
        with open(path, "rb") as handle:
            size = os.fstat(handle.fileno()).st_size
            if size > MAX_INPUT_BYTES:
                raise _CliError(2, f"input file exceeds {MAX_INPUT_BYTES} bytes")
            data = handle.read(MAX_INPUT_BYTES + 1)
    except _CliError:
        raise
    except OSError as exc:
        raise _CliError(3, f"cannot read input file: {exc}") from exc
    if len(data) > MAX_INPUT_BYTES:
        raise _CliError(2, f"input file exceeds {MAX_INPUT_BYTES} bytes")
    return data


def _reject_duplicate_keys(pairs):
    seen = set()
    for key, _value in pairs:
        if key in seen:
            raise ValueError("duplicate object key in JSON input")
        seen.add(key)
    return dict(pairs)


def _reject_constant(token):
    raise ValueError(f"invalid JSON numeric constant: {token}")


def _load_interactions(data):
    """Decode and parse the input bytes; all parse errors become ValueError."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("input file is not valid UTF-8") from exc
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("input file is not valid JSON") from exc
    except RecursionError as exc:
        # Deeply nested JSON exhausts the decoder's recursion limit instead of
        # raising JSONDecodeError; treat it as invalid input, not a crash.
        raise ValueError("input file is not valid JSON") from exc
    if not isinstance(payload, list):
        raise ValueError("interactions must be a JSON array")
    return payload


def _parse_limit(raw_limit):
    message = f"limit must be an integer between {MIN_LIMIT} and {MAX_LIMIT}"
    if not isinstance(raw_limit, str) or _LIMIT_PATTERN.fullmatch(raw_limit) is None:
        raise ValueError(message)
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise ValueError(message) from exc
    if not MIN_LIMIT <= limit <= MAX_LIMIT:
        raise ValueError(message)
    return limit


def _run_recommend(args, parser):
    try:
        limit = _parse_limit(args.limit)
    except ValueError as exc:
        parser.error(str(exc))

    try:
        data = _read_input_bytes(args.file)
    except _CliError as exc:
        _write_error(exc.message)
        return exc.code

    try:
        interactions = _load_interactions(data)
        result = recommend(interactions, args.user, limit)
    except ValueError as exc:
        _write_error(exc)
        return 2

    payload = json.dumps(result, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    _write_stdout(payload + "\n")
    return 0


def main(argv=None):
    """Run the command-line interface and return the process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.error("a command is required")
    if args.command == "recommend":
        return _run_recommend(args, parser)
    parser.error(f"unknown command: {args.command}")  # pragma: no cover
    return 2  # pragma: no cover
