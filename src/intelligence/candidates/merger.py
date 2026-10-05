"""Merges overlapping candidates from different generators."""

from __future__ import annotations

from src.domain.models import Candidate


def merge_candidates(candidates: list[Candidate]) -> list[Candidate]:
    """
    Merge overlapping candidates. 
    If Candidate A and B overlap by > 50%, merge them into a single Candidate
    with the combined generators and reason_codes.
    """
    if not candidates:
        return []
        
    # Sort by start time
    sorted_cands = sorted(candidates, key=lambda c: c.event_start)
    merged = [sorted_cands[0]]
    
    for current in sorted_cands[1:]:
        last = merged[-1]
        
        # Check overlap
        overlap_start = max(last.event_start, current.event_start)
        overlap_end = min(last.event_end, current.event_end)
        overlap_duration = max(0.0, overlap_end - overlap_start)
        
        min_duration = min(last.event_end - last.event_start, current.event_end - current.event_start)
        
        if min_duration > 0 and (overlap_duration / min_duration) > 0.5:
            # Merge
            last.event_start = min(last.event_start, current.event_start)
            last.event_end = max(last.event_end, current.event_end)
            last.generators = list(set(last.generators + current.generators))
            last.reason_codes = list(set(last.reason_codes + current.reason_codes))
            last.evidence.update(current.evidence)
        else:
            merged.append(current)
            
    return merged
