# expense-tracker

Console expense tracker. Stores records in SQLite, sums by category and by
month. Money is handled as integer cents, so no rounding drift.

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Usage

```
uv run expense-tracker add AMOUNT CATEGORY [--date YYYY-MM-DD] [--db PATH]
uv run expense-tracker list [--category NAME] [--db PATH]
uv run expense-tracker total [--month YYYY-MM] [--db PATH]
uv run expense-tracker delete ID [--db PATH]
```

`--db` works before or after the subcommand. Without it, the database lives at
`~/.expense-tracker/expenses.db`.

`add` defaults the date to today.

### add

```bash
uv run expense-tracker add 1250.00 rent --date 2026-03-01
uv run expense-tracker add 42.90 groceries
```

```
added #1: 1250.00 rent on 2026-03-01
added #2: 42.90 groceries
```

The amount must be a positive number with at most two decimals. The category
is lowercased and stripped, so `Food` and `  food  ` both become `food`.

### list

Newest first.

```bash
uv run expense-tracker list
```

```
#4 2026-04-02     340.25 groceries
#3 2026-03-05      15.00 coffee
#2 2026-03-03      42.90 groceries
#1 2026-03-01    1250.00 rent
```

Filter by category:

```bash
uv run expense-tracker list --category groceries
```

```
#4 2026-04-02     340.25 groceries
#2 2026-03-03      42.90 groceries
```

An empty database prints `no expenses recorded`.

### total

Grouped by category, with a grand total:

```bash
uv run expense-tracker total
```

```
coffee                      15.00
groceries                  383.15
rent                      1250.00
TOTAL                     1648.15
```

For a single month:

```bash
uv run expense-tracker total --month 2026-03
```

```
total for 2026-03: 1307.90
```

No expenses in the period means `0.00`.

### delete

```bash
uv run expense-tracker delete 3
```

```
deleted #3
```

Deleting an unknown id is not an error.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | success |
| 1 | validation error, message on stderr |
| 2 | wrong arguments |

```
$ uv run expense-tracker add abc food
error: amount must be a positive number with at most 2 decimals: 'abc'
```

## Development

```bash
uv run pytest                    # tests
uv run pytest tests/test_cli.py -v
uv run ruff check .              # lint
uv run ruff format .             # format
```

Layout:

```
src/expense_tracker/models.py      domain objects and validation, no I/O
src/expense_tracker/repository.py  SQLite persistence, the only SQL
src/expense_tracker/cli.py         argparse front end, no SQL
tests/                             one pytest module per source module
```

See `AGENTS.md` for the conventions this project expects from contributors and
agents.
