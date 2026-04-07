"""Unit tests for LightRAG service adapters and guards."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from app.ai import lightrag_service


class _FakeEmbeddingsClient:
    """Minimal async embeddings client for OpenAI call sequencing tests."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def create(self, *, model: str, input):
        self.calls.append({"model": model, "input": input})
        if not self._responses:
            raise AssertionError("No fake responses left")
        vectors = self._responses.pop(0)
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=v) for v in vectors]
        )


@pytest.mark.asyncio
async def test_openai_embed_retries_when_batch_cardinality_mismatch(monkeypatch):
    """When a batch returns wrong vector count, fallback retries one by one."""
    fake_embeddings = _FakeEmbeddingsClient(
        responses=[
            [[1.0], [2.0], [3.0]],  # initial batch: wrong count (3 for 2 inputs)
            [[10.0]],               # retry for first text
            [[20.0]],               # retry for second text
        ]
    )

    class _FakeAsyncOpenAI:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.embeddings = fake_embeddings

    monkeypatch.setattr(lightrag_service, "AsyncOpenAI", _FakeAsyncOpenAI)

    result = await lightrag_service._openai_embed(
        texts=["alpha", "beta"],
        model="text-embedding-3-large",
        api_key="test-key",
    )

    assert isinstance(result, np.ndarray)
    assert result.tolist() == [[10.0], [20.0]]
    assert fake_embeddings.calls[0]["input"] == ["alpha", "beta"]
    assert fake_embeddings.calls[1]["input"] == ["alpha"]
    assert fake_embeddings.calls[2]["input"] == ["beta"]


def test_normalize_embedding_texts_handles_non_string_inputs():
    """Non-string and nested values are normalized to plain strings."""
    values = [
        "hi",
        None,
        123,
        {"k": "v"},
        ["nested", 1],
    ]

    normalized = lightrag_service._normalize_embedding_texts(values)

    assert normalized[0] == "hi"
    assert normalized[1] == ""
    assert normalized[2] == "123"
    assert normalized[3].startswith("{")
    assert normalized[4].startswith("[")
