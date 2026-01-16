"""
Pytest configuration and fixtures for decidalo_client tests.
"""

import pytest
from aioresponses import aioresponses


@pytest.fixture
def mock_aiohttp() -> aioresponses:  # type: ignore[misc]
    """Fixture providing aioresponses mock."""
    with aioresponses() as m:
        yield m
