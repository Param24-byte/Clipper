"""Candidates base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import Candidate


class CandidateGenerator(ABC):
    """Base class for all candidate generators."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the generator (e.g., 'SemanticStrongStatement')."""
        ...
        
    @abstractmethod
    async def generate(self, source_id: str, index_data: dict, **kwargs) -> list[Candidate]:
        """Analyze index data and return potentially interesting moments."""
        ...
