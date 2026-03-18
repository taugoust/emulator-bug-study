import pytest
import os
import tempfile
from bug_classifier.config import load_config, CategoryConfig


class TestCategoryConfig:
    def test_all_property(self):
        cfg = CategoryConfig(positive=["a", "b"], negative=["c"], architectures=["x"])
        assert cfg.all_categories == ["a", "b", "c", "x"]

    def test_empty_lists(self):
        cfg = CategoryConfig(positive=[], negative=[], architectures=[])
        assert cfg.all_categories == []


class TestLoadConfig:
    def test_loads_valid_toml(self):
        content = """
[categories]
positive = ["semantic", "TCG"]
negative = ["boot", "network"]
architectures = ["x86", "arm"]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(content)
            f.flush()
            cfg = load_config(f.name)
        os.unlink(f.name)

        assert cfg.positive == ["semantic", "TCG"]
        assert cfg.negative == ["boot", "network"]
        assert cfg.architectures == ["x86", "arm"]
        assert cfg.all_categories == ["semantic", "TCG", "boot", "network", "x86", "arm"]

    def test_missing_field_raises(self):
        content = """
[categories]
positive = ["a"]
negative = ["b"]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(content)
            f.flush()
            with pytest.raises(KeyError):
                load_config(f.name)
        os.unlink(f.name)

    def test_missing_section_raises(self):
        content = """
[other]
key = "value"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(content)
            f.flush()
            with pytest.raises(KeyError):
                load_config(f.name)
        os.unlink(f.name)

    def test_qemu_config(self):
        """Verify the shipped qemu.toml loads correctly."""
        cfg = load_config("data/configs/qemu.toml")
        assert "semantic" in cfg.positive
        assert "boot" in cfg.negative
        assert "x86" in cfg.architectures
        assert len(cfg.all_categories) == len(cfg.positive) + len(cfg.negative) + len(cfg.architectures)
