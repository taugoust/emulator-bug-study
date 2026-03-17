import pytest
import os
import tempfile
from buglib.files import write_file, list_files_recursive


class TestWriteFile:
    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "file.txt")
            write_file(path, "hello")
            assert open(path).read() == "hello"

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "a", "b", "c", "file.txt")
            write_file(path, "nested")
            assert os.path.exists(path)

    def test_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "file.txt")
            write_file(path, "first")
            write_file(path, "second")
            assert open(path).read() == "second"


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

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = list_files_recursive(tmpdir)
            assert result == []
