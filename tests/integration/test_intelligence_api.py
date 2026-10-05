"""Integration tests for intelligence API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_transcribe_and_index_jobs(client: AsyncClient):
    # 1. Create a project
    resp = await client.post("/projects", json={"owner_id": "user123", "name": "Test Intelligence Project"})
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

    # 3. Enqueue transcribe job
    resp = await client.post(
        "/jobs/transcribe",
        json={
            "project_id": project_id,
            "source_id": source_id,
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["stage"] == "transcribe"
    assert data["state"] == "queued"
    
    # 4. Duplicate transcribe should 409
    resp_dup = await client.post(
        "/jobs/transcribe",
        json={
            "project_id": project_id,
            "source_id": source_id,
        },
    )
    assert resp_dup.status_code == 409

    # 5. Enqueue index job
    resp_idx = await client.post(
        "/jobs/index",
        json={
            "project_id": project_id,
            "source_id": source_id,
        },
    )
    assert resp_idx.status_code == 202
    data_idx = resp_idx.json()
    assert data_idx["stage"] == "index"
    assert data_idx["state"] == "queued"

    # 6. Enqueue discover job
    resp_disc = await client.post(
        "/jobs/discover",
        json={
            "project_id": project_id,
            "source_id": source_id,
        },
    )
    assert resp_disc.status_code == 202
    data_disc = resp_disc.json()
    assert data_disc["stage"] == "discover_candidates"
    assert data_disc["state"] == "queued"

    # 7. Enqueue resolve job
    resp_res = await client.post(
        "/jobs/resolve",
        json={
            "project_id": project_id,
            "source_id": source_id,
        },
    )
    assert resp_res.status_code == 202
    
    # 8. Enqueue rank job
    resp_rank = await client.post(
        "/jobs/rank",
        json={
            "project_id": project_id,
            "source_id": source_id,
        },
    )
    assert resp_rank.status_code == 202
    data_rank = resp_rank.json()
    assert data_rank["stage"] == "rank"
    assert data_rank["state"] == "queued"
    
    # 9. Enqueue EDL job
    resp_edl = await client.post(
        "/jobs/edl",
        json={
            "project_id": project_id,
            "source_id": source_id,
        },
    )
    assert resp_edl.status_code == 202
    data_edl = resp_edl.json()
    assert data_edl["stage"] == "generate_edl"
    assert data_edl["state"] == "queued"
