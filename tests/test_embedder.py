"""Tests for ingestion/embedder.py. Uses MockEmbedder exclusively --
never OpenAIEmbedder -- so this test file can never spend money."""

from __future__ import annotations

from pathlib import Path

from ingestion.embedder import EmbeddingCache, MockEmbedder


def test_mock_embedder_is_deterministic():
    e = MockEmbedder(dimension=8)
    v1 = e.embed(["hello world"])[0]
    v2 = e.embed(["hello world"])[0]
    assert v1 == v2


def test_mock_embedder_different_text_different_vector():
    e = MockEmbedder(dimension=8)
    v1 = e.embed(["hello world"])[0]
    v2 = e.embed(["goodbye world"])[0]
    assert v1 != v2


def test_mock_embedder_dimension_respected():
    e = MockEmbedder(dimension=16)
    v = e.embed(["x"])[0]
    assert len(v) == 16
    assert e.dimension == 16


def test_embedding_cache_round_trip(tmp_path):
    cache = EmbeddingCache(tmp_path / "cache.json")
    assert cache.get("model-a", "text") is None
    cache.put("model-a", "text", [1.0, 2.0, 3.0])
    assert cache.get("model-a", "text") == [1.0, 2.0, 3.0]

    cache.save()
    reloaded = EmbeddingCache(tmp_path / "cache.json")
    assert reloaded.get("model-a", "text") == [1.0, 2.0, 3.0]


def test_embedding_cache_keys_by_model_too():
    cache = EmbeddingCache(Path("/tmp/never_written_unused_path.json"))
    cache.put("model-a", "same text", [1.0])
    cache.put("model-b", "same text", [2.0])
    assert cache.get("model-a", "same text") == [1.0]
    assert cache.get("model-b", "same text") == [2.0]
