"""Shared fixtures for the Home Assistant tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> Generator[None]:
    """Make custom_components/ visible to Home Assistant in every test."""
    yield
