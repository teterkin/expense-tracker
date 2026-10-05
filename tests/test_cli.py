import csv
from pathlib import Path

import pytest

from expense_tracker.cli import DEFAULT_DB, main
from expense_tracker.models import InvalidAmount, InvalidCategory
from expense_tracker.repository import ExpenseRepository


@pytest.fixture
def db(tmp_path):
    return tmp_path / "expenses.db"


def run(db, *args):
    return main([*args, "--db", str(db)])


class TestDbOptionPlacement:
    def test_db_flag_before_subcommand_is_honoured(self, tmp_path, capsys):
        target = tmp_path / "before.db"

        main(["--db", str(target), "add", "1.00", "food"])

        assert target.exists()

    def test_db_flag_after_subcommand_is_honoured(self, tmp_path, capsys):
        target = tmp_path / "after.db"

        main(["add", "1.00", "food", "--db", str(target)])

        assert target.exists()

    def test_global_flag_after_subcommand_overrides_default(self, tmp_path):
        target = tmp_path / "override.db"

        main(["--db", str(tmp_path / "ignored.db"), "add", "1.00", "food"])
        main(["add", "2.00", "food", "--db", str(target)])

        stored = ExpenseRepository(target).list_all()
        assert [e.cents for e in stored] == [200]


class TestAddCommand:
    def test_prints_confirmation_with_amount_and_category(self, db, capsys):
        exit_code = run(db, "add", "12.34", "food", "--date", "2026-03-05")

        out = capsys.readouterr().out
        assert exit_code == 0
        assert "12.34" in out
        assert "food" in out

    def test_uses_today_when_date_is_omitted(self, db, capsys):
        run(db, "add", "1.00", "food")

        assert "food" in capsys.readouterr().out

    def test_returns_error_code_for_invalid_amount(self, db, capsys):
        exit_code = run(db, "add", "abc", "food")

        assert exit_code == 1
        assert "amount" in capsys.readouterr().err

    def test_returns_error_code_for_invalid_category(self, db, capsys):
        exit_code = run(db, "add", "10.00", "!!")

        assert exit_code == 1
        assert "category" in capsys.readouterr().err

    def test_returns_error_code_for_malformed_date(self, db, capsys):
        exit_code = run(db, "add", "10.00", "food", "--date", "05.03.2026")

        assert exit_code == 1
        assert "date" in capsys.readouterr().err


class TestListCommand:
    def test_reports_empty_database(self, db, capsys):
        exit_code = run(db, "list")

        assert exit_code == 0
        assert "no expenses" in capsys.readouterr().out

    def test_lists_expenses_newest_first(self, db, capsys):
        run(db, "add", "1.00", "food", "--date", "2026-03-01")
        run(db, "add", "2.00", "transport", "--date", "2026-03-10")
        capsys.readouterr()

        run(db, "list")

        out = capsys.readouterr().out
        assert out.index("2.00") < out.index("1.00")

    def test_filters_by_category(self, db, capsys):
        run(db, "add", "1.00", "food")
        run(db, "add", "2.00", "transport")
        capsys.readouterr()

        run(db, "list", "--category", "food")

        out = capsys.readouterr().out
        assert "1.00" in out
        assert "2.00" not in out

    def test_reports_no_matches_for_unknown_category(self, db, capsys):
        run(db, "add", "1.00", "food")
        capsys.readouterr()

        exit_code = run(db, "list", "--category", "fun")

        assert exit_code == 0
        assert "no expenses" in capsys.readouterr().out


class TestTotalCommand:
    def test_prints_totals_grouped_by_category(self, db, capsys):
        run(db, "add", "10.00", "food")
        run(db, "add", "2.50", "food")
        run(db, "add", "7.25", "transport")
        capsys.readouterr()

        exit_code = run(db, "total")

        out = capsys.readouterr().out
        assert exit_code == 0
        assert "food" in out
        assert "12.50" in out
        assert "7.25" in out

    def test_prints_total_for_single_month(self, db, capsys):
        run(db, "add", "10.00", "food", "--date", "2026-03-05")
        run(db, "add", "99.00", "food", "--date", "2026-04-05")
        capsys.readouterr()

        run(db, "total", "--month", "2026-03")

        out = capsys.readouterr().out
        assert "10.00" in out
        assert "99.00" not in out

    def test_reports_zero_for_month_without_expenses(self, db, capsys):
        exit_code = run(db, "total", "--month", "2026-12")

        assert exit_code == 0
        assert "0.00" in capsys.readouterr().out

    def test_returns_error_code_for_malformed_month(self, db, capsys):
        exit_code = run(db, "total", "--month", "2026-13")

        assert exit_code == 1
        assert "month" in capsys.readouterr().err

    def test_reports_zero_for_empty_database(self, db, capsys):
        exit_code = run(db, "total")

        assert exit_code == 0
        assert "0.00" in capsys.readouterr().out


class TestDeleteCommand:
    def test_removes_expense_and_prints_confirmation(self, db, capsys):
        run(db, "add", "1.00", "food")
        capsys.readouterr()

        run(db, "delete", "1")

        assert "deleted" in capsys.readouterr().out.lower()
        run(db, "list")
        assert "no expenses" in capsys.readouterr().out

    def test_deleting_unknown_id_is_not_an_error(self, db, capsys):
        exit_code = run(db, "delete", "999")

        assert exit_code == 0


class TestExportCommand:
    def test_writes_header_to_stdout_for_empty_database(self, db, capsys):
        exit_code = run(db, "export")

        assert exit_code == 0
        assert capsys.readouterr().out == "id,date,amount,category\n"

    def test_writes_one_row_per_expense_in_list_order(self, db, capsys):
        run(db, "add", "1.00", "food", "--date", "2026-03-01")
        run(db, "add", "2.50", "transport", "--date", "2026-03-10")
        capsys.readouterr()

        run(db, "export")

        rows = list(csv.reader(capsys.readouterr().out.splitlines()))
        assert [(row[0], row[1], row[3]) for row in rows[1:]] == [
            ("2", "2026-03-10", "transport"),
            ("1", "2026-03-01", "food"),
        ]

    def test_writes_amount_as_decimal_string_not_cents(self, db, capsys):
        run(db, "add", "2.50", "transport", "--date", "2026-03-10")
        capsys.readouterr()

        run(db, "export")

        rows = list(csv.reader(capsys.readouterr().out.splitlines()))
        assert rows[1][2] == "2.50"

    def test_stdout_contains_nothing_but_csv(self, db, capsys):
        run(db, "add", "1.00", "food", "--date", "2026-03-01")
        capsys.readouterr()

        exit_code = run(db, "export")

        assert exit_code == 0
        assert capsys.readouterr().out == "id,date,amount,category\n1,2026-03-01,1.00,food\n"

    def test_output_flag_writes_same_csv_to_file(self, db, tmp_path, capsys):
        run(db, "add", "1.00", "food", "--date", "2026-03-01")
        run(db, "add", "2.50", "transport", "--date", "2026-03-10")
        capsys.readouterr()
        target = tmp_path / "out.csv"

        exit_code = run(db, "export", "-o", str(target))

        assert exit_code == 0
        assert target.read_text(encoding="utf-8") == (
            "id,date,amount,category\n2,2026-03-10,2.50,transport\n1,2026-03-01,1.00,food\n"
        )

    def test_unwritable_output_path_returns_error_code(self, db, tmp_path, capsys):
        missing = tmp_path / "nope" / "out.csv"

        exit_code = run(db, "export", "-o", str(missing))

        assert exit_code == 1
        assert "out.csv" in capsys.readouterr().err

    def test_file_lines_use_lf_not_crlf(self, db, tmp_path, capsys):
        run(db, "add", "1.00", "food", "--date", "2026-03-01")
        capsys.readouterr()
        target = tmp_path / "out.csv"

        run(db, "export", "-o", str(target))

        assert target.read_bytes() == b"id,date,amount,category\n1,2026-03-01,1.00,food\n"


class TestUnknownCommand:
    def test_returns_error_code(self, db, capsys):
        exit_code = run(db, "nonsense")

        assert exit_code == 2
        assert "nonsense" in capsys.readouterr().err


class TestErrorMessages:
    def test_invalid_amount_message_names_the_field_and_offending_value(self, capsys, db):
        run(db, "add", "abc", "food")

        err = capsys.readouterr().err
        assert "amount" in err
        assert "abc" in err

    def test_invalid_category_message_names_the_field_and_offending_value(self, capsys, db):
        run(db, "add", "10.00", "!!")

        err = capsys.readouterr().err
        assert "category" in err
        assert "!!" in err


def test_exceptions_are_value_errors():
    assert issubclass(InvalidAmount, ValueError)
    assert issubclass(InvalidCategory, ValueError)


def test_default_db_is_in_user_home():
    assert DEFAULT_DB.parent == Path.home() / ".expense-tracker"
