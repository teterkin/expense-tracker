from datetime import date

import pytest

from expense_tracker.models import Expense
from expense_tracker.repository import ExpenseRepository


@pytest.fixture
def repo(tmp_path):
    return ExpenseRepository(tmp_path / "expenses.db")


def make(amount: str, category: str, day: int = 5) -> Expense:
    return Expense(amount=amount, category=category, spent_on=date(2026, 3, day))


class TestAdd:
    def test_added_expense_can_be_read_back(self, repo):
        repo.add(make("12.34", "food"))

        stored = repo.list_all()

        assert len(stored) == 1
        assert stored[0].cents == 1234
        assert stored[0].category == "food"
        assert stored[0].spent_on == date(2026, 3, 5)

    def test_assigns_incrementing_ids(self, repo):
        first = repo.add(make("1.00", "food"))
        second = repo.add(make("2.00", "transport"))

        assert second.id == first.id + 1

    def test_data_survives_reopening_the_database(self, tmp_path):
        path = tmp_path / "expenses.db"
        ExpenseRepository(path).add(make("9.99", "food"))

        reopened = ExpenseRepository(path).list_all()

        assert reopened[0].cents == 999


class TestListAll:
    def test_returns_empty_list_when_no_expenses(self, repo):
        assert repo.list_all() == []

    def test_orders_newest_first(self, repo):
        repo.add(make("1.00", "food", day=1))
        repo.add(make("2.00", "food", day=10))
        repo.add(make("3.00", "food", day=20))

        assert [e.spent_on.day for e in repo.list_all()] == [20, 10, 1]


class TestListByCategory:
    def test_returns_only_matching_category(self, repo):
        repo.add(make("1.00", "food"))
        repo.add(make("2.00", "transport"))
        repo.add(make("3.00", "food"))

        food = repo.list_by_category("FOOD")

        assert len(food) == 2
        assert all(e.category == "food" for e in food)

    def test_returns_empty_list_for_unknown_category(self, repo):
        repo.add(make("1.00", "food"))

        assert repo.list_by_category("fun") == []


class TestTotals:
    def test_total_by_category_sums_cents(self, repo):
        repo.add(make("10.00", "food"))
        repo.add(make("2.50", "food"))
        repo.add(make("7.25", "transport"))

        totals = repo.total_by_category()

        assert totals["food"] == 1250
        assert totals["transport"] == 725

    def test_total_by_category_is_empty_for_no_expenses(self, repo):
        assert repo.total_by_category() == {}

    def test_total_by_category_for_month_sums_cents(self, repo):
        repo.add(make("10.00", "food"))
        repo.add(make("2.50", "food"))
        repo.add(make("7.25", "transport"))

        totals = repo.total_by_category_for_month(2026, 3)

        assert totals == {"food": 1250, "transport": 725}

    def test_total_by_category_for_month_ignores_other_months(self, repo):
        repo.add(make("10.00", "food"))
        repo.add(Expense(amount="99.00", category="food", spent_on=date(2026, 4, 5)))

        totals = repo.total_by_category_for_month(2026, 3)

        assert totals == {"food": 1000}

    def test_total_by_category_for_month_is_empty_without_expenses(self, repo):
        repo.add(make("10.00", "food"))

        assert repo.total_by_category_for_month(2026, 12) == {}

    def test_total_for_month_ignores_other_months(self, repo):
        repo.add(Expense(amount="10.00", category="food", spent_on=date(2026, 3, 5)))
        repo.add(Expense(amount="99.00", category="food", spent_on=date(2026, 4, 5)))

        total = repo.total_for_month(2026, 3)

        assert total == 1000

    def test_total_for_month_without_expenses_is_zero(self, repo):
        assert repo.total_for_month(2026, 12) == 0

    @pytest.mark.parametrize("month", [0, -1, 13])
    def test_total_by_category_for_month_rejects_out_of_range_month(self, repo, month):
        with pytest.raises(ValueError, match="month must be in 1..12"):
            repo.total_by_category_for_month(2026, month)

    def test_month_total_equals_sum_of_category_totals(self, repo):
        repo.add(make("10.00", "food"))
        repo.add(make("2.50", "food"))
        repo.add(make("7.25", "transport"))

        totals = repo.total_by_category_for_month(2026, 3)

        assert sum(totals.values()) == repo.total_for_month(2026, 3) == 1975

    def test_rejects_out_of_range_month(self, repo):
        with pytest.raises(ValueError):
            repo.total_for_month(2026, 13)


class TestDelete:
    def test_deletes_expense_by_id(self, repo):
        saved = repo.add(make("1.00", "food"))

        repo.delete(saved.id)

        assert repo.list_all() == []

    def test_deleting_unknown_id_does_nothing(self, repo):
        repo.add(make("1.00", "food"))

        repo.delete(999)

        assert len(repo.list_all()) == 1
