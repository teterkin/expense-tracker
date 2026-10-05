from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from expense_tracker.models import Expense, InvalidAmount, InvalidCategory
from expense_tracker.repository import ExpenseRepository

DEFAULT_DB = Path.home() / ".expense-tracker" / "expenses.db"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser.

    ``--db`` is accepted both before and after the subcommand. Subparsers use
    ``SUPPRESS`` as the default so that a value parsed by the root parser is
    not overwritten with the fallback path.
    """
    db_help = "path to the SQLite database"

    def add_db_option(subparser: argparse.ArgumentParser, default: object) -> None:
        subparser.add_argument("--db", type=Path, default=default, help=db_help)

    parser = argparse.ArgumentParser(prog="expense-tracker", description="Track expenses.")
    add_db_option(parser, DEFAULT_DB)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add", help="record an expense")
    add.add_argument("amount")
    add.add_argument("category")
    add.add_argument("--date", help="ISO date, defaults to today")
    add_db_option(add, argparse.SUPPRESS)

    listing = subparsers.add_parser("list", help="show expenses")
    listing.add_argument("--category", help="filter by category")
    add_db_option(listing, argparse.SUPPRESS)

    total = subparsers.add_parser("total", help="sum expenses")
    total.add_argument("--month", help="month as YYYY-MM")
    add_db_option(total, argparse.SUPPRESS)

    delete = subparsers.add_parser("delete", help="remove an expense by id")
    delete.add_argument("id", type=int)
    add_db_option(delete, argparse.SUPPRESS)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return an exit code: 0 ok, 1 validation, 2 arguments."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    _ensure_db_parent(args.db)
    repo = ExpenseRepository(args.db)

    try:
        if args.command == "add":
            return _cmd_add(repo, args)
        if args.command == "list":
            return _cmd_list(repo, args)
        if args.command == "total":
            return _cmd_total(repo, args)
        if args.command == "delete":
            return _cmd_delete(repo, args)
    except (InvalidAmount, InvalidCategory, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"error: unknown command {args.command!r}", file=sys.stderr)
    return 2


def _ensure_db_parent(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _cmd_add(repo: ExpenseRepository, args: argparse.Namespace) -> int:
    try:
        spent_on = date.fromisoformat(args.date) if args.date else date.today()
    except ValueError:
        print(f"error: date must be in ISO format YYYY-MM-DD, got {args.date!r}", file=sys.stderr)
        return 1
    saved = repo.add(Expense(amount=args.amount, category=args.category, spent_on=spent_on))
    print(f"added #{saved.id}: {saved.formatted_amount} {saved.category} on {spent_on.isoformat()}")
    return 0


def _cmd_list(repo: ExpenseRepository, args: argparse.Namespace) -> int:
    expenses = repo.list_by_category(args.category) if args.category else repo.list_all()
    if not expenses:
        print("no expenses recorded")
        return 0
    for expense in expenses:
        print(
            f"#{expense.id} {expense.spent_on.isoformat()} "
            f"{expense.formatted_amount:>10} {expense.category}"
        )
    return 0


def _cmd_total(repo: ExpenseRepository, args: argparse.Namespace) -> int:
    if args.month:
        try:
            year_text, month_text = args.month.split("-")
            cents = repo.total_for_month(int(year_text), int(month_text))
        except ValueError:
            print(f"error: month must be in YYYY-MM format, got {args.month!r}", file=sys.stderr)
            return 1
        print(f"total for {args.month}: {_format_cents(cents)}")
        return 0

    totals = repo.total_by_category()
    if not totals:
        print("total: 0.00")
        return 0
    grand_total = 0
    for category, cents in sorted(totals.items()):
        print(f"{category:<20} {_format_cents(cents):>12}")
        grand_total += cents
    print(f"{'TOTAL':<20} {_format_cents(grand_total):>12}")
    return 0


def _cmd_delete(repo: ExpenseRepository, args: argparse.Namespace) -> int:
    repo.delete(args.id)
    print(f"deleted #{args.id}")
    return 0


def _format_cents(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


if __name__ == "__main__":
    raise SystemExit(main())
