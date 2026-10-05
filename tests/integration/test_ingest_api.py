"""Integration tests for ingest API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_ingest_job(client: AsyncClient):
    # 1. Create a project
    resp = await client.post("/projects", json={"owner_id": "user123", "name": "Test Project"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # 2. Create a source
    resp = await client.post(
        "/sources",
        json={
            "project_id": project_id,
            "type": "youtube",
            "uri": "https://www.youtube.com/watch?v=123",
        },
    )
    assert resp.status_code == 201
    source_id = resp.json()["id"]

    # 3. Enqueue ingest job
    resp = await client.post(
        "/jobs/ingest",
        json={
            "project_id": project_id,
            "source_id": source_id,
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["project_id"] == project_id
    assert data["source_id"] == source_id
    assert data["stage"] == "ingest"
    assert data["state"] == "queued"
    
    # 4. Duplicate should 409
    resp2 = await client.post(
        "/jobs/ingest",
        json={
            "project_id": project_id,
            "source_id": source_id,
        },
    )
    assert resp2.status_code == 409
