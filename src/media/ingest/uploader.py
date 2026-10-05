"""Local file upload handler stub."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.telemetry.logging import get_logger

logger = get_logger(__name__)


def copy_uploaded_file(uri: str, output_dir: Path) -> Path:
    """
    'Uploads' a local file by copying it into the working directory.
    URI format for local files: file:///path/to/file.mp4 or /path/to/file.mp4
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    local_path = uri.replace("file://", "")
    src_path = Path(local_path).expanduser().resolve()
    
    if not src_path.exists():
        raise FileNotFoundError(f"Uploaded file not found: {src_path}")
        
    dest_path = output_dir / src_path.name
    
    logger.debug("copy_uploaded_file_started", src=str(src_path), dest=str(dest_path))
    shutil.copy2(src_path, dest_path)
    logger.debug("copy_uploaded_file_completed")
    
    return dest_path
