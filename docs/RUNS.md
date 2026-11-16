# Run record

Per-run bookkeeping required by the delivery contract (spec §7.9). Unknown or
unobservable values are recorded as `null` rather than guessed. Raw results and
results after any judge correction are kept separate; this file contains the
raw record only, because no judge correction was observed in this session.

## Run 1 — implementation

| Field | Value |
| --- | --- |
| ID | issue-1 / run-1 |
| Stage | implementation + public tests (single session) |
| Spec version | 0.1.4 |
| Spec hash | null (spec text is not stored in this repository) |
| Judge hash | null (no judge correction observed) |
| Requested model | null (not observable from the repository) |
| Observed model | `deepseek-flash` (harness session metadata) |
| Model source | harness session metadata |
| Tokens / cost | null / null (not observable from the repository) |
| Turns | null (not exported to the repository) |
| Correction rounds | 0 observed |
| Stop reason | task completed; local commit handed to the harness |
| Human interventions | none observed in the implementation session |
| Verdict | pending maintainer review and CI; no verdict claimed |
| External verification source | null (none performed in this session) |

### Raw results

- Local test suite: `python -m pytest tests -q` — see the maintainer-run log;
  the command is the reproducible source of truth.
- Local lint: `ruff check .` and `ruff format --check .`.
- Windows and Ubuntu CI results are recorded by GitHub Actions, not by this
  file; no CI verdict is asserted here.
- Independent hidden tests and the spec×test audit are external to this clone
  and were neither read nor executed during implementation.
