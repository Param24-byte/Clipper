"""Faster-whisper wrapper for transcription."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

from src.telemetry.logging import get_logger

logger = get_logger(__name__)


def transcribe_audio(audio_path: Path, model_size: str = "base") -> dict[str, Any]:
    """
    Transcribe audio using faster-whisper.
    Returns a dictionary of transcript segments and words.
    """
    logger.info("transcribe_audio_started", audio_path=str(audio_path), model=model_size)
    
    # Run on CPU by default for dev, fallback to GPU if needed/available
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(str(audio_path), word_timestamps=True)
    
    logger.info("transcribe_audio_info", language=info.language, duration=info.duration)
    
    result_segments = []
    result_words = []
    
    for segment in segments:
        result_segments.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
        })
        if segment.words:
            for word in segment.words:
                result_words.append({
                    "start": word.start,
                    "end": word.end,
                    "word": word.word.strip(),
                    "probability": word.probability,
                })

    logger.info("transcribe_audio_completed", num_segments=len(result_segments), num_words=len(result_words))
    
    return {
        "duration": info.duration,
        "language": info.language,
        "segments": result_segments,
        "words": result_words,
    }
