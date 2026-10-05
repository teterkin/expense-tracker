from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from expense_tracker.models import Expense

_SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cents INTEGER NOT NULL,
    category TEXT NOT NULL,
    spent_on TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_expenses_spent_on ON expenses (spent_on);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses (category);
"""


def _month_prefix(year: int, month: int) -> str:
    if not 1 <= month <= 12:
        raise ValueError(f"month must be in 1..12, got {month}")
    return f"{year:04d}-{month:02d}"


class ExpenseRepository:
    def __init__(self, db_path: Path | str) -> None:
        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(_SCHEMA)

    def add(self, expense: Expense) -> Expense:
        cursor = self._connection.execute(
            "INSERT INTO expenses (cents, category, spent_on) VALUES (?, ?, ?)",
            (expense.cents, expense.category, expense.spent_on.isoformat()),
        )
        self._connection.commit()
        return Expense(
            amount=expense.formatted_amount,
            category=expense.category,
            spent_on=expense.spent_on,
            id=cursor.lastrowid,
        )

    def list_all(self) -> list[Expense]:
        rows = self._connection.execute(
            "SELECT id, cents, category, spent_on FROM expenses ORDER BY spent_on DESC, id DESC"
        ).fetchall()
        return [self._to_expense(row) for row in rows]

    def list_by_category(self, category: str) -> list[Expense]:
        rows = self._connection.execute(
            "SELECT id, cents, category, spent_on FROM expenses "
            "WHERE category = ? ORDER BY spent_on DESC, id DESC",
            (category.strip().lower(),),
        ).fetchall()
        return [self._to_expense(row) for row in rows]

    def total_by_category(self) -> dict[str, int]:
        rows = self._connection.execute(
            "SELECT category, SUM(cents) AS total FROM expenses GROUP BY category"
        ).fetchall()
        return {row["category"]: row["total"] for row in rows}

    def total_for_month(self, year: int, month: int) -> int:
        row = self._connection.execute(
            "SELECT COALESCE(SUM(cents), 0) AS total FROM expenses "
            "WHERE substr(spent_on, 1, 7) = ?",
            (_month_prefix(year, month),),
        ).fetchone()
        return row["total"]

    def total_by_category_for_month(self, year: int, month: int) -> dict[str, int]:
        rows = self._connection.execute(
            "SELECT category, SUM(cents) AS total FROM expenses "
            "WHERE substr(spent_on, 1, 7) = ? GROUP BY category",
            (_month_prefix(year, month),),
        ).fetchall()
        return {row["category"]: row["total"] for row in rows}

    def delete(self, expense_id: int) -> None:
        self._connection.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        self._connection.commit()

    @staticmethod
    def _to_expense(row: sqlite3.Row) -> Expense:
        whole, cents = divmod(row["cents"], 100)
        return Expense(
            amount=f"{whole}.{cents:02d}",
            category=row["category"],
            spent_on=date.fromisoformat(row["spent_on"]),
            id=row["id"],
        )
