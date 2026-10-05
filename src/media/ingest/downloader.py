"""yt-dlp wrapper for downloading YouTube URLs."""

from __future__ import annotations

import yt_dlp
from pathlib import Path

from src.telemetry.logging import get_logger

logger = get_logger(__name__)


def download_youtube_video(uri: str, output_dir: Path) -> Path:
    """
    Download a YouTube video using yt-dlp.
    Returns the Path to the downloaded video file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # yt-dlp config
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(output_dir / "downloaded_%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    logger.debug("yt_dlp_download_started", uri=uri)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(uri, download=True)
            if not info:
                raise RuntimeError(f"Could not extract info for {uri}")
            
            # Find the final filename
            expected_filename = ydl.prepare_filename(info)
            final_path = Path(expected_filename)
            
            # If merge happened, the extension might be replaced
            if not final_path.exists():
                final_path = final_path.with_suffix(".mp4")
            
            if not final_path.exists():
                raise FileNotFoundError(f"Downloaded file not found at {final_path}")
                
            logger.debug("yt_dlp_download_completed", path=str(final_path))
            return final_path
    except Exception as e:
        logger.error("yt_dlp_download_failed", error=str(e), uri=uri)
        raise RuntimeError(f"Failed to download {uri}: {e}") from e
