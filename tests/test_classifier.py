import pytest
import os
import tempfile
from bug_classifier.main import get_category, compare_category, write_output
from buglib import list_files_recursive
from time import monotonic


POSITIVE = ['semantic', 'TCG', 'assembly', 'architecture', 'mistranslation', 'register', 'user-level']
NEGATIVE = ['boot', 'network', 'kvm', 'vnc', 'graphic', 'device', 'socket', 'debug', 'files', 'PID', 'permissions', 'performance', 'kernel', 'peripherals', 'VMM', 'hypervisor', 'virtual', 'other']
ARCHITECTURES = ['x86', 'arm', 'risc-v', 'i386', 'ppc']


class TestGetCategorySingleLabel:
    """Tests with multi_label=False: always returns the highest-scoring label."""

    def test_returns_highest(self):
        classification = {
            'labels': ['network', 'boot', 'kvm'],
            'scores': [0.95, 0.5, 0.3]
        }
        assert get_category(classification, POSITIVE, NEGATIVE, ARCHITECTURES, False) == 'network'

    def test_positive_category(self):
        classification = {
            'labels': ['mistranslation', 'boot', 'kvm'],
            'scores': [0.95, 0.5, 0.3]
        }
        assert get_category(classification, POSITIVE, NEGATIVE, ARCHITECTURES, False) == 'mistranslation'


class TestGetCategoryMultiLabel:
    """Tests with multi_label=True: applies threshold logic."""

    def test_all_low_scores(self):
        classification = {
            'labels': ['network', 'boot'],
            'scores': [0.7, 0.6]
        }
        assert get_category(classification, POSITIVE, NEGATIVE, ARCHITECTURES, True) == 'none'

    def test_small_spread(self):
        classification = {
            'labels': ['network', 'boot'],
            'scores': [0.9, 0.85]
        }
        assert get_category(classification, POSITIVE, NEGATIVE, ARCHITECTURES, True) == 'unknown'

    def test_negative_high_score(self):
        classification = {
            'labels': ['network', 'semantic', 'boot'],
            'scores': [0.95, 0.85, 0.3]
        }
        assert get_category(classification, POSITIVE, NEGATIVE, ARCHITECTURES, True) == 'network'

    def test_positive_with_arch(self):
        classification = {
            'labels': ['mistranslation', 'x86', 'boot'],
            'scores': [0.9, 0.85, 0.3]
        }
        result = get_category(classification, POSITIVE, NEGATIVE, ARCHITECTURES, True)
        assert result == 'mistranslation-x86'

    def test_arch_then_positive(self):
        classification = {
            'labels': ['x86', 'assembly', 'boot'],
            'scores': [0.9, 0.85, 0.3]
        }
        result = get_category(classification, POSITIVE, NEGATIVE, ARCHITECTURES, True)
        assert result == 'assembly-x86'


class TestCompareCategory:
    def test_positive_high_score_keeps_category(self):
        classification = {
            'labels': ['semantic', 'boot'],
            'scores': [0.9, 0.5]
        }
        assert compare_category(classification, 'semantic', POSITIVE) == 'semantic'

    def test_no_match_returns_review(self):
        classification = {
            'labels': ['boot', 'network'],
            'scores': [0.5, 0.3]
        }
        assert compare_category(classification, 'semantic', POSITIVE) == 'review'


class TestListFilesRecursive:
    def test_flat_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ['a', 'b', 'c']:
                open(os.path.join(tmpdir, name), 'w').close()
            result = list_files_recursive(tmpdir)
            assert len(result) == 3

    def test_nested_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, 'sub')
            os.makedirs(subdir)
            open(os.path.join(tmpdir, 'a'), 'w').close()
            open(os.path.join(subdir, 'b'), 'w').close()
            result = list_files_recursive(tmpdir)
            assert len(result) == 2

    def test_basename_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, 'sub')
            os.makedirs(subdir)
            open(os.path.join(subdir, 'myfile'), 'w').close()
            result = list_files_recursive(tmpdir, basename=True)
            assert result == ['myfile']

    def test_nonexistent_directory(self):
        result = list_files_recursive('/nonexistent/path')
        assert result == []


class TestWriteOutput:
    def test_creates_output_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            start = monotonic()
            write_output("bug text", "network", ["network", "boot"], [0.9, 0.5], "bug123", tmpdir, start)
            out_path = os.path.join(tmpdir, "network", "bug123")
            assert os.path.exists(out_path)
            content = open(out_path).read()
            assert "network: 0.900" in content
            assert "bug text" in content

    def test_creates_reasoning_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            start = monotonic()
            write_output("bug text", "network", [], [], "bug123", tmpdir, start, reasoning="because reasons")
            reasoning_path = os.path.join(os.path.dirname(tmpdir), "reasoning", "network", "bug123")
            assert os.path.exists(reasoning_path)
            assert "because reasons" in open(reasoning_path).read()
