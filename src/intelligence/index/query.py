"""Query helpers for the media index."""

from __future__ import annotations


class MediaIndexQuery:
    """Helper to query the parsed media_index.json data."""
    
    def __init__(self, index_data: dict):
        self.data = index_data
        
    def get_sentences_in_range(self, start_time: float, end_time: float) -> list[dict]:
        """Return all sentences that fall entirely within the given time range."""
        results = []
        for s in self.data.get("sentences", []):
            if s["start"] >= start_time and s["end"] <= end_time:
                results.append(s)
        return results
        
    def get_words_in_range(self, start_time: float, end_time: float) -> list[dict]:
        """Return all words that fall entirely within the given time range."""
        results = []
        for w in self.data.get("words", []):
            if w["start"] >= start_time and w["end"] <= end_time:
                results.append(w)
        return results
