"""Audio-based candidate generators."""

from __future__ import annotations

from src.api.ids import new_id
from src.domain.models import Candidate
from src.intelligence.candidates.base import CandidateGenerator


class HighEnergySpike(CandidateGenerator):
    """Finds moments of high audio energy (e.g. laughter, shouting).
    For now, uses a mock heuristic based on duration of speaking segments between silences.
    """
    
    @property
    def name(self) -> str:
        return "HighEnergySpike"
        
    async def generate(self, source_id: str, index_data: dict, **kwargs) -> list[Candidate]:
        # A real implementation would parse volume/RMS data from index.
        # We will mock it by finding any sentence shorter than 2s (quick interjection).
        candidates = []
        sentences = index_data.get("sentences", [])
        
        for s in sentences:
            duration = s["end"] - s["start"]
            if 0.5 < duration < 2.0:
                candidates.append(Candidate(
                    id=new_id(),
                    source_id=source_id,
                    event_start=s["start"],
                    event_end=s["end"],
                    generators=[self.name],
                    reason_codes=["SHORT_INTERJECTION"],
                    evidence={"duration": duration, "text": s["text"]}
                ))
                
        return candidates
