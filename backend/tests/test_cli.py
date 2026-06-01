"""Tests for CLI interface."""

import subprocess
import sys


class TestCLI:
    def test_version_command(self):
        result = subprocess.run(
            [sys.executable, "-m", "marginalia.cli", "version"],
            capture_output=True,
            text=True,
            cwd=str(__import__("pathlib").Path(__file__).parent.parent),
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )
        assert result.returncode == 0
        assert "marginalia-ai" in result.stdout

    def test_analyze_command_inline(self):
        review = (
            "This paper presents an interesting contribution. "
            "The methodology is well-described. I recommend acceptance."
        )
        result = subprocess.run(
            [sys.executable, "-m", "marginalia.cli", "analyze", review],
            capture_output=True,
            text=True,
            cwd=str(__import__("pathlib").Path(__file__).parent.parent),
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )
        assert result.returncode == 0
        assert "Ghost Score" in result.stdout

    def test_analyze_command_json_output(self):
        review = (
            "This paper presents an interesting contribution. "
            "The methodology is well-described. I recommend acceptance."
        )
        result = subprocess.run(
            [sys.executable, "-m", "marginalia.cli", "analyze", "--json", review],
            capture_output=True,
            text=True,
            cwd=str(__import__("pathlib").Path(__file__).parent.parent),
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )
        assert result.returncode == 0
        import json
        data = json.loads(result.stdout)
        assert "overall" in data
        assert "label" in data
        assert 0 <= data["overall"] <= 100

    def test_help_command(self):
        result = subprocess.run(
            [sys.executable, "-m", "marginalia.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=str(__import__("pathlib").Path(__file__).parent.parent),
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )
        assert result.returncode == 0
        assert "analyze" in result.stdout
        assert "scan" in result.stdout
