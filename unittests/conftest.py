"""
Pytest configuration and fixtures for decidalo_client tests.
"""

from collections.abc import Iterator

import pytest
from aioresponses import aioresponses


@pytest.fixture
def mock_aiohttp() -> Iterator[aioresponses]:
    """Fixture providing aioresponses mock."""
    with aioresponses() as m:
        yield m
