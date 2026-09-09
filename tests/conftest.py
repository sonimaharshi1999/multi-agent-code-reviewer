# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.message_bus import MessageBus
from src.models import FileAnalysis, ReviewProfile


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def bus() -> MessageBus:
    """Fresh message bus for each test."""
    return MessageBus()


@pytest.fixture
def standard_profile() -> ReviewProfile:
    return ReviewProfile.STANDARD


@pytest.fixture
def thorough_profile() -> ReviewProfile:
    return ReviewProfile.THOROUGH


def make_file_analysis(source: str, file_path: str = "<test>") -> FileAnalysis:
    """Helper to create a FileAnalysis from raw source code."""
    return FileAnalysis(
        file_path=file_path,
        source_code=source,
        line_count=len(source.splitlines()),
        ast_valid=True,
    )


def load_fixture(name: str) -> FileAnalysis:
    """Load a fixture file into a FileAnalysis."""
    path = FIXTURES_DIR / name
    source = path.read_text(encoding="utf-8")
    return FileAnalysis(
        file_path=str(path),
        source_code=source,
        line_count=len(source.splitlines()),
        ast_valid=True,
    )
