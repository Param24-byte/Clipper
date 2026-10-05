"""Unit tests for ingest pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import SourceRow
from src.domain.models import SourceType
from src.media.ffmpeg.probe import MediaProbeResult
from src.media.ingest.pipeline import run_ingest


@pytest.fixture
def mock_downloader():
    with patch("src.media.ingest.pipeline.download_youtube_video") as mock:
        yield mock


@pytest.fixture
def mock_uploader():
    with patch("src.media.ingest.pipeline.copy_uploaded_file") as mock:
        yield mock


@pytest.fixture
def mock_probe():
    with patch("src.media.ingest.pipeline.probe") as mock:
        yield mock


@pytest.fixture
def mock_extract_audio():
    with patch("src.media.ingest.pipeline.extract_audio") as mock:
        yield mock


@pytest.fixture
def mock_generate_proxy():
    with patch("src.media.ingest.pipeline.generate_proxy") as mock:
        yield mock


@pytest.mark.asyncio
async def test_run_ingest_youtube(
    db: AsyncSession,
    mock_downloader,
    mock_probe,
    mock_extract_audio,
    mock_generate_proxy,
    tmp_path,
):
    source_id = "01HYBXXXXX"
    uri = "https://youtube.com/watch?v=123"
    
    # Setup source row
    source = SourceRow(
        id=source_id,
        project_id="01PROJECTXXX",
        type="youtube",
        uri=uri,
        metadata={},
    )
    db.add(source)
    await db.commit()
    
    # Mock behavior
    fake_video = tmp_path / "video.mp4"
    fake_video.write_text("fake video data")
    mock_downloader.return_value = fake_video
    
    mock_probe.return_value = MediaProbeResult(
        duration_seconds=120.0,
        width=1920,
        height=1080,
        fps=30.0,
        has_audio=True,
        codec_video="h264",
        codec_audio="aac",
        raw={"format": {"duration": "120.0"}}
    )
    
    # We mock extract_audio and generate_proxy to just create dummy files
    def fake_extract(in_path, out_path):
        out_path.write_text("fake audio")
    
    def fake_proxy(in_path, out_path):
        out_path.write_text("fake proxy")
        
    mock_extract_audio.side_effect = fake_extract
    mock_generate_proxy.side_effect = fake_proxy
    
    # Create a mock store
    class MockStore:
        async def exists(self, key): return False
        async def put(self, key, data, content_type=None): return f"local://{key}"
        async def get_uri(self, key): return f"local://{key}"
    
    store = MockStore()
    
    # Run
    artifacts = await run_ingest(source_id, uri, SourceType.YOUTUBE, store, db)
    
    # Verify
    assert len(artifacts) == 4  # source, audio, proxy, probe
    assert mock_downloader.called
    assert mock_probe.called
    assert mock_extract_audio.called
    assert mock_generate_proxy.called
    
    # Check DB updates
    await db.refresh(source)
    assert source.checksum is not None
    assert source.duration_seconds == 120.0
    assert source.width == 1920
    assert source.height == 1080
    assert source.fps == 30.0
