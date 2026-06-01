"""Tests for cache layer."""

import asyncio

import pytest

from marginalia.data.cache import InMemoryCache


@pytest.mark.asyncio
async def test_in_memory_set_and_get():
    cache = InMemoryCache()
    await cache.set("k1", {"value": 42})
    result = await cache.get("k1")
    assert result == {"value": 42}


@pytest.mark.asyncio
async def test_in_memory_missing_key_returns_none():
    cache = InMemoryCache()
    assert await cache.get("missing") is None


@pytest.mark.asyncio
async def test_in_memory_ttl_expires():
    cache = InMemoryCache()
    await cache.set("temp", "data", ttl_seconds=0)
    await asyncio.sleep(0.01)
    assert await cache.get("temp") is None


@pytest.mark.asyncio
async def test_in_memory_delete():
    cache = InMemoryCache()
    await cache.set("k", "v")
    await cache.delete("k")
    assert await cache.get("k") is None


@pytest.mark.asyncio
async def test_in_memory_complex_data():
    cache = InMemoryCache()
    data = {"nested": {"list": [1, 2, 3], "bool": True}}
    await cache.set("complex", data)
    assert await cache.get("complex") == data
