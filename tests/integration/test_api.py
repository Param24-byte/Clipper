"""Integration tests — API endpoints using the test DB."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    # degraded is OK in test env (Redis may be absent)
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data


async def test_create_project(client: AsyncClient):
    resp = await client.post(
        "/projects",
        json={"owner_id": "01J000000000000000000OWNER", "name": "Test Project"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Project"
    assert data["status"] == "created"
    assert "id" in data


async def test_get_project(client: AsyncClient):
    # Create then retrieve
    create_resp = await client.post(
        "/projects",
        json={"owner_id": "01J000000000000000000OWNER", "name": "Fetch Me"},
    )
    project_id = create_resp.json()["id"]

    get_resp = await client.get(f"/projects/{project_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == project_id


async def test_get_project_not_found(client: AsyncClient):
    resp = await client.get("/projects/NONEXISTENTIDXXXXXX")
    assert resp.status_code == 404


async def test_create_source(client: AsyncClient):
    proj = await client.post(
        "/projects",
        json={"owner_id": "01J000000000000000000OWNER", "name": "Source Project"},
    )
    project_id = proj.json()["id"]

    resp = await client.post(
        "/sources",
        json={
            "project_id": project_id,
            "type": "youtube",
            "uri": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["project_id"] == project_id
    assert data["type"] == "youtube"


async def test_create_source_invalid_project(client: AsyncClient):
    resp = await client.post(
        "/sources",
        json={
            "project_id": "01JNONEXISTENTPROJECT00000",  # 26 chars, doesn't exist
            "type": "youtube",
            "uri": "https://www.youtube.com/watch?v=abc",
        },
    )
    assert resp.status_code == 404


async def test_get_source_not_found(client: AsyncClient):
    resp = await client.get("/sources/NONEXISTENTSOURCE")
    assert resp.status_code == 404
