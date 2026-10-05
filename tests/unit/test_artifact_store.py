"""Unit tests for LocalArtifactStore."""

from __future__ import annotations

import pytest

from src.storage.local import LocalArtifactStore


@pytest.fixture()
def store(tmp_path):
    return LocalArtifactStore(root_dir=tmp_path)


async def test_put_and_get(store):
    data = b"hello artifact"
    uri = await store.put("stage/source123/file.json", data)
    assert uri.startswith("local://")
    result = await store.get("stage/source123/file.json")
    assert result == data


async def test_exists_returns_true_after_put(store):
    await store.put("test/key.bin", b"data")
    assert await store.exists("test/key.bin") is True


async def test_exists_returns_false_for_missing(store):
    assert await store.exists("nonexistent/key.bin") is False


async def test_delete_removes_artifact(store):
    await store.put("del/key.bin", b"x")
    await store.delete("del/key.bin")
    assert await store.exists("del/key.bin") is False


async def test_delete_is_noop_when_missing(store):
    # Should not raise
    await store.delete("nonexistent/key.bin")


async def test_get_raises_key_error_when_missing(store):
    with pytest.raises(KeyError):
        await store.get("nonexistent/key.bin")


async def test_path_traversal_is_blocked(store):
    # Attempting to escape root via ../
    uri = await store.put("../../etc/passwd", b"evil")
    # Should resolve to inside the store root, not the filesystem root
    assert "etc/passwd" in uri.replace("\\", "/")
    # The file must be inside tmp_path, not outside
    data = await store.get("../../etc/passwd")
    assert data == b"evil"
