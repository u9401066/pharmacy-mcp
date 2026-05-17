"""Tests for disk-backed cache behavior."""

from pharmacy_mcp.infrastructure.cache.disk_cache import CacheService


def test_cache_json_round_trip_and_falsy_values(tmp_path):
    """Disk cache preserves structured data and falsy scalar values."""
    cache = CacheService(cache_dir=str(tmp_path / "cache"))
    try:
        assert cache.set("payload", {"count": 0, "items": ["a"]})
        assert cache.get("payload") == {"count": 0, "items": ["a"]}

        assert cache.set("zero", 0)
        assert cache.get("zero") == 0
        assert "zero" in cache

        assert cache.delete("zero")
        assert cache.get("zero") is None
    finally:
        cache.close()


def test_cache_get_or_set_only_calls_factory_on_miss(tmp_path):
    """get_or_set reuses cached values without calling the factory again."""
    cache = CacheService(cache_dir=str(tmp_path / "cache"))
    calls = 0

    def build_value() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"calls": calls}

    try:
        assert cache.get_or_set("computed", build_value) == {"calls": 1}
        assert cache.get_or_set("computed", build_value) == {"calls": 1}
        assert calls == 1
    finally:
        cache.close()
