"""Signal extraction from media (silence, scenes, etc)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def detect_silence(audio_path: Path, noise_tolerance: str = "-30dB", duration: float = 1.0) -> list[dict]:
    """
    Detect silence regions using FFmpeg silencedetect filter.
    Returns a list of dicts: {"start": float, "end": float}
    """
    cmd = [
        "ffmpeg",
        "-i", str(audio_path),
        "-af", f"silencedetect=noise={noise_tolerance}:d={duration}",
        "-f", "null",
        "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    silences = []
    current_start = None
    
    # Parse FFmpeg output which looks like:
    # [silencedetect @ 0x...] silence_start: 45.2
    # [silencedetect @ 0x...] silence_end: 47.8 | silence_duration: 2.6
    for line in result.stderr.splitlines():
        if "silence_start:" in line:
            parts = line.split("silence_start: ")
            if len(parts) > 1:
                current_start = float(parts[1].split()[0])
        elif "silence_end:" in line and current_start is not None:
            parts = line.split("silence_end: ")
            if len(parts) > 1:
                end_time = float(parts[1].split()[0])
                silences.append({"start": current_start, "end": end_time})
                current_start = None

    return silences
