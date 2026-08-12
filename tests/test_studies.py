from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


def _write_fake_command(directory: Path, name: str) -> None:
    command = directory / name
    command.write_text(
        "#!/bin/sh\n"
        'printf \'%s\\n\' "$0 $*" >> "$COMMAND_LOG"\n'
    )
    command.chmod(0o755)


@pytest.mark.parametrize(
    ("study", "credential_tool", "expected_classifier_calls"),
    (
        ("box64", "gh", 1),
        ("qemu", "glab", 2),
        ("angr", "gh", 1),
    ),
)
def test_study_uses_installed_tool_names(
    tmp_path: Path,
    study: str,
    credential_tool: str,
    expected_classifier_calls: int,
) -> None:
    command_directory = tmp_path / "bin"
    command_directory.mkdir()
    for name in (
        credential_tool,
        "scrape",
        "bug-classifier",
        "analyze-csv",
        "word-count",
    ):
        _write_fake_command(command_directory, name)

    command_log = tmp_path / "commands.log"
    environment = os.environ.copy()
    environment.update(
        {
            "COMMAND_LOG": str(command_log),
            "DATA_DIR": str(tmp_path / "data"),
            "OUTPUT_DIR": str(tmp_path / "output"),
            "PATH": f"{command_directory}:{environment['PATH']}",
        }
    )
    environment.pop("GITHUB_TOKEN", None)
    environment.pop("GITLAB_TOKEN", None)

    subprocess.run(
        ["bash", f"studies/{study}.sh"],
        check=True,
        env=environment,
    )

    commands = command_log.read_text().splitlines()
    classifier_commands = [
        command for command in commands if "/bug-classifier " in command
    ]
    assert len(classifier_commands) == expected_classifier_calls
    assert all("--config data/configs/" in command for command in classifier_commands)
    assert not any("bug-classify " in command for command in commands)


def test_classifier_help_uses_installed_command_name() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from bug_classifier.main import main; main()",
            "--help",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.startswith("usage: bug-classifier ")
