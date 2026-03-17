import pytest
from datetime import datetime
from scrape.mailinglist import is_bug, months_iterator


class TestIsBug:
    def test_bug_uppercase(self):
        assert is_bug("[BUG] something broke")

    def test_bug_lowercase(self):
        assert is_bug("[bug] something broke")

    def test_bug_mixed_case(self):
        assert is_bug("[Bug] something broke")

    def test_bug_with_number(self):
        assert is_bug("[Bug 1234567] something broke")

    def test_bug_with_extra_text_in_brackets(self):
        assert is_bug("[PATCH BUG fix] something broke")

    def test_no_bug(self):
        assert not is_bug("[PATCH] something changed")

    def test_no_brackets(self):
        assert not is_bug("BUG something broke")

    def test_empty(self):
        assert not is_bug("")


class TestMonthsIterator:
    def test_single_month(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1)
        months = list(months_iterator(start, end))
        assert len(months) == 1
        assert months[0] == datetime(2024, 1, 1)

    def test_same_year(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 3, 1)
        months = list(months_iterator(start, end))
        assert len(months) == 3
        assert months[0] == datetime(2024, 1, 1)
        assert months[1] == datetime(2024, 2, 1)
        assert months[2] == datetime(2024, 3, 1)

    def test_year_boundary(self):
        start = datetime(2024, 11, 1)
        end = datetime(2025, 2, 1)
        months = list(months_iterator(start, end))
        assert len(months) == 4
        assert months[0] == datetime(2024, 11, 1)
        assert months[1] == datetime(2024, 12, 1)
        assert months[2] == datetime(2025, 1, 1)
        assert months[3] == datetime(2025, 2, 1)

    def test_end_before_start(self):
        start = datetime(2025, 1, 1)
        end = datetime(2024, 1, 1)
        months = list(months_iterator(start, end))
        assert len(months) == 0
