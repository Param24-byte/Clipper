"""FFprobe wrapper for extracting media metadata."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MediaProbeResult:
    duration_seconds: float
    width: int | None
    height: int | None
    fps: float | None
    has_audio: bool
    codec_video: str | None
    codec_audio: str | None
    raw: dict


def probe(path: Path) -> MediaProbeResult:
    """Run ffprobe on the given path and return structured metadata."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path)
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFprobe failed for {path}: {e.stderr}") from e

    data = json.loads(result.stdout)
    
    streams = data.get("streams", [])
    format_info = data.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(format_info.get("duration", 0.0))
    if duration == 0.0 and video_stream:
        duration = float(video_stream.get("duration", 0.0))

    width = int(video_stream.get("width")) if video_stream and "width" in video_stream else None
    height = int(video_stream.get("height")) if video_stream and "height" in video_stream else None
    
    fps = None
    if video_stream and "r_frame_rate" in video_stream:
        num, den = video_stream["r_frame_rate"].split("/")
        if float(den) > 0:
            fps = float(num) / float(den)

    return MediaProbeResult(
        duration_seconds=duration,
        width=width,
        height=height,
        fps=fps,
        has_audio=audio_stream is not None,
        codec_video=video_stream.get("codec_name") if video_stream else None,
        codec_audio=audio_stream.get("codec_name") if audio_stream else None,
        raw=data
    )
