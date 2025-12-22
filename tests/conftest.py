"""Test configuration and fixtures."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from pharmacy_mcp.infrastructure.api.rxnorm import RxNormClient
from pharmacy_mcp.infrastructure.api.fda import FDAClient
from pharmacy_mcp.infrastructure.cache.disk_cache import CacheService


@pytest.fixture
def mock_cache():
    """Mock cache service."""
    cache = MagicMock(spec=CacheService)
    cache.get.return_value = None
    cache.set.return_value = True
    return cache


@pytest.fixture
def mock_rxnorm_client():
    """Mock RxNorm client."""
    client = AsyncMock(spec=RxNormClient)
    return client


@pytest.fixture
def mock_fda_client():
    """Mock FDA client."""
    client = AsyncMock(spec=FDAClient)
    return client
