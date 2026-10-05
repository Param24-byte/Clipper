"""FFmpeg wrappers for proxy and audio generation."""

from __future__ import annotations

import subprocess
from pathlib import Path

from src.telemetry.logging import get_logger

logger = get_logger(__name__)


def extract_audio(input_path: Path, output_path: Path) -> None:
    """Extract audio as 16kHz mono WAV (ideal for Whisper)."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vn",                   # No video
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-ar", "16000",          # 16 kHz sample rate
        "-ac", "1",              # Mono
        str(output_path)
    ]
    logger.debug("extract_audio_started", input=str(input_path), output=str(output_path))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error("extract_audio_failed", stderr=e.stderr)
        raise RuntimeError(f"FFmpeg audio extraction failed: {e.stderr}") from e
    logger.debug("extract_audio_completed")


def generate_proxy(input_path: Path, output_path: Path) -> None:
    """Generate a 720p H.264 proxy video for fast editing/preview."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vf", "scale=-2:720",   # Scale to 720p, preserve aspect ratio
        "-c:v", "libx264",       # H.264 encoding
        "-preset", "fast",       # Fast encoding
        "-crf", "23",            # Constant rate factor (quality)
        "-c:a", "aac",           # AAC audio
        "-b:a", "128k",
        str(output_path)
    ]
    logger.debug("generate_proxy_started", input=str(input_path), output=str(output_path))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error("generate_proxy_failed", stderr=e.stderr)
        raise RuntimeError(f"FFmpeg proxy generation failed: {e.stderr}") from e
    logger.debug("generate_proxy_completed")
