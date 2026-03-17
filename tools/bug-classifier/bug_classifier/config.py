"""Load category configuration from a TOML file."""

from __future__ import annotations
import tomllib
from dataclasses import dataclass


@dataclass
class CategoryConfig:
    """Category lists for classification."""
    positive: list[str]
    negative: list[str]
    architectures: list[str]

    @property
    def all(self) -> list[str]:
        return self.positive + self.negative + self.architectures


def load_config(path: str) -> CategoryConfig:
    """Load a category configuration from a TOML file.

    Expected format::

        [categories]
        positive = ["semantic", "TCG", ...]
        negative = ["boot", "network", ...]
        architectures = ["x86", "arm", ...]
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)

    cats = data["categories"]
    return CategoryConfig(
        positive=cats["positive"],
        negative=cats["negative"],
        architectures=cats["architectures"],
    )
