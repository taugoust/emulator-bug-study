import pytest
import os
import tempfile
from analyze_csv.main import parse_iteration, output_csv
from analyze_diff.main import find_changes, output_diff
from io import StringIO


class TestParseIteration:
    def test_counts_files_per_category(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for cat in ['network', 'boot']:
                cat_dir = os.path.join(tmpdir, cat)
                os.makedirs(cat_dir)
                for i in range(3 if cat == 'network' else 1):
                    open(os.path.join(cat_dir, f'bug{i}'), 'w').close()

            result = parse_iteration(tmpdir)
            assert result['network'] == 3
            assert result['boot'] == 1

    def test_ignores_files_at_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, 'stray_file'), 'w').close()
            cat_dir = os.path.join(tmpdir, 'network')
            os.makedirs(cat_dir)
            open(os.path.join(cat_dir, 'bug1'), 'w').close()

            result = parse_iteration(tmpdir)
            assert 'stray_file' not in result
            assert result['network'] == 1

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = parse_iteration(tmpdir)
            assert result == {}


class TestOutputCsv:
    def test_format(self):
        buf = StringIO()
        output_csv({'network': 5, 'boot': 2}, buf)
        lines = buf.getvalue().strip().split('\n')
        assert lines[0] == "category, count"
        assert "network, 5" in lines
        assert "boot, 2" in lines


class TestFindChanges:
    def test_detects_category_change(self):
        with tempfile.TemporaryDirectory() as old, tempfile.TemporaryDirectory() as new:
            # bug1 moved from network to boot
            os.makedirs(os.path.join(old, 'network'))
            os.makedirs(os.path.join(new, 'boot'))
            open(os.path.join(old, 'network', 'bug1'), 'w').close()
            open(os.path.join(new, 'boot', 'bug1'), 'w').close()

            changes = find_changes(old, new)
            assert len(changes) == 1
            assert changes[0]['name'] == 'bug1'
            assert changes[0]['old'] == 'network'
            assert changes[0]['new'] == 'boot'

    def test_no_changes(self):
        with tempfile.TemporaryDirectory() as old, tempfile.TemporaryDirectory() as new:
            os.makedirs(os.path.join(old, 'network'))
            os.makedirs(os.path.join(new, 'network'))
            open(os.path.join(old, 'network', 'bug1'), 'w').close()
            open(os.path.join(new, 'network', 'bug1'), 'w').close()

            changes = find_changes(old, new)
            assert len(changes) == 0

    def test_new_file_not_a_change(self):
        with tempfile.TemporaryDirectory() as old, tempfile.TemporaryDirectory() as new:
            os.makedirs(os.path.join(new, 'network'))
            open(os.path.join(new, 'network', 'bug1'), 'w').close()

            changes = find_changes(old, new)
            assert len(changes) == 0


class TestOutputDiff:
    def test_format(self):
        changes = [{'name': 'bug1', 'old': 'network', 'new': 'boot'}]
        buf = StringIO()
        output_diff(changes, buf)
        text = buf.getvalue()
        assert "1 changes:" in text
        assert "bug1: network -> boot" in text
