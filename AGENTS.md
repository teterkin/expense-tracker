# Project rules

Complement the global rules in `~/.config/opencode/AGENTS.md` — they do not
replace them.

## Stack and structure

- Python 3.12, packaged with `uv`. Standard src layout.
- `src/expense_tracker/models.py` — domain value objects and validation. No I/O.
- `src/expense_tracker/repository.py` — SQLite persistence. Only place with SQL.
- `src/expense_tracker/cli.py` — argparse CLI, returns an exit code, no SQL.
- `tests/` — pytest, one module per source module.

## Commands

All verified to exist:

```bash
# install
uv sync

# test
uv run pytest

# test with coverage-free verbose output for one area
uv run pytest tests/test_models.py -v

# lint
uv run ruff check .

# format
uv run ruff format .

# verify formatting
uv run ruff format --check .

# run
uv run expense-tracker add 12.34 food
uv run expense-tracker list
uv run expense-tracker total --month 2026-03
```

There is no typechecker configured. Do not claim typecheck results.

## Conventions

- Money is always `int` cents. Never `float`, never `Decimal` at the model
  boundary. `parse_cents` is the single entry point for parsing user input.
- Amount accepts at most 2 decimal digits and must be greater than zero.
- Categories are lowercased and stripped on the way in, in
  `normalize_category`. Callers never normalize on their own.
- `Expense` is a frozen dataclass with `slots`. Do not add setters.
- Dates are `datetime.date`, stored as ISO strings in SQLite.
- Repository methods return `Expense` objects, never sqlite rows.
- CLI prints user-facing text and returns `0` on success, `1` on a validation
  error, `2` on an argument error. Errors go to stderr.
- The CLI catches `ValueError` subclasses at the dispatch level. Do not add
  per-command try/except for validation errors.

## Domain notes

- A repository instance owns one `sqlite3` connection. Tests use `tmp_path`;
  there is no global connection and no in-memory shortcut.
- Totals are computed in SQL, not in Python. Do not sum in application code.
- `list_all` and `list_by_category` order by `spent_on DESC, id DESC`.
- Deleting an unknown id is a no-op and is not an error.
