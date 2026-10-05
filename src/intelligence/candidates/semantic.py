"""Semantic candidate generators."""

from __future__ import annotations

import json
from src.api.ids import new_id
from src.domain.models import Candidate
from src.intelligence.candidates.base import CandidateGenerator
from src.intelligence.llm.adapter import get_llm_adapter
from src.telemetry.logging import get_logger

logger = get_logger(__name__)


class SemanticStrongStatement(CandidateGenerator):
    """Finds bold, controversial, or highly quotable statements using LLM."""
    
    @property
    def name(self) -> str:
        return "SemanticStrongStatement"
        
    async def generate(self, source_id: str, index_data: dict, **kwargs) -> list[Candidate]:
        llm = get_llm_adapter()
        
        sentences = index_data.get("sentences", [])
        if not sentences:
            return []
            
        # Group sentences into chunks of ~10 for LLM context (simple approach)
        candidates = []
        chunk_size = 10
        
        # In a real app we'd process in parallel, but here we process the first 2 chunks to save time/tokens for demo
        for i in range(0, min(len(sentences), 20), chunk_size):
            chunk = sentences[i:i+chunk_size]
            transcript_text = "\n".join([f"[{s['start']:.1f} - {s['end']:.1f}] {s['text']}" for s in chunk])
            
            prompt = f"""
            Analyze the following transcript excerpt and identify 1 or 2 highly quotable, strong, or controversial statements.
            Return a JSON object with a 'moments' array. Each moment must have:
            - 'start': float (start time)
            - 'end': float (end time)
            - 'reason': string (why it's a strong statement)
            - 'quote': string (the exact text)
            
            Transcript:
            {transcript_text}
            """
            
            try:
                response = await llm.generate_json(prompt)
                for moment in response.get("moments", []):
                    c = Candidate(
                        id=new_id(),
                        source_id=source_id,
                        event_start=moment["start"],
                        event_end=moment["end"],
                        generators=[self.name],
                        reason_codes=["STRONG_QUOTE"],
                        evidence={"quote": moment.get("quote"), "reason": moment.get("reason")}
                    )
                    candidates.append(c)
            except Exception as e:
                logger.error("semantic_generator_failed", error=str(e))
                
        return candidates
