# Public tests

Run the whole public suite with one command:

```console
$ python -m pytest tests -q
```

- `test_lib.py` exercises only `local_recommender.recommend`, the documented
  public API.
- `test_cli.py` exercises `app` through `subprocess` with `sys.executable`,
  never by importing a private module.
- Test names and module docstrings cite acceptance criteria `AC-1` … `AC-12`.
- The normative ambiguity resolutions followed by the tests are summarised in
  `AMBIGUIDADES.md`.

No test downloads dependencies or uses the network. Temporary directories and
subprocesses are per-test; no global state is shared.
