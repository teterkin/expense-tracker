from datetime import date

import pytest

from expense_tracker.models import Expense, InvalidAmount, InvalidCategory


class TestExpenseAmount:
    def test_parses_decimal_string_into_cents(self):
        expense = Expense(amount="12.34", category="food", spent_on=date(2026, 1, 5))

        assert expense.cents == 1234

    def test_parses_amount_without_fractional_part(self):
        expense = Expense(amount="100", category="food", spent_on=date(2026, 1, 5))

        assert expense.cents == 10000

    @pytest.mark.parametrize("amount", ["0", "0.00", "-5", "-0.01"])
    def test_rejects_non_positive_amounts(self, amount):
        with pytest.raises(InvalidAmount):
            Expense(amount=amount, category="food", spent_on=date(2026, 1, 5))

    @pytest.mark.parametrize("amount", ["", "abc", "1.2.3", "10,50", "$12"])
    def test_rejects_amounts_that_are_not_positive_numbers(self, amount):
        with pytest.raises(InvalidAmount):
            Expense(amount=amount, category="food", spent_on=date(2026, 1, 5))

    def test_rejects_amount_with_more_than_two_fraction_digits(self):
        with pytest.raises(InvalidAmount):
            Expense(amount="10.005", category="food", spent_on=date(2026, 1, 5))


class TestExpenseCategory:
    def test_normalizes_category_to_lowercase(self):
        expense = Expense(amount="10", category="FOOD", spent_on=date(2026, 1, 5))

        assert expense.category == "food"

    def test_strips_surrounding_whitespace(self):
        expense = Expense(amount="10", category="  food  ", spent_on=date(2026, 1, 5))

        assert expense.category == "food"

    @pytest.mark.parametrize("category", ["", "   ", "!@#"])
    def test_rejects_blank_or_non_alphanumeric_categories(self, category):
        with pytest.raises(InvalidCategory):
            Expense(amount="10", category=category, spent_on=date(2026, 1, 5))


class TestExpenseFormatting:
    def test_formats_cents_with_two_decimals(self):
        expense = Expense(amount="1234.5", category="food", spent_on=date(2026, 1, 5))

        assert expense.formatted_amount == "1234.50"

    def test_is_immutable(self):
        expense = Expense(amount="10", category="food", spent_on=date(2026, 1, 5))

        with pytest.raises(AttributeError):
            expense.cents = 1
