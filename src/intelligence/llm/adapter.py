"""LLM Adapter interface."""

from __future__ import annotations

import os
from typing import Protocol, Any


class LLMAdapter(Protocol):
    async def generate_json(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        """Generate a JSON response from the LLM."""
        ...


class GeminiAdapter:
    """Google Gemini implementation."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiAdapter")
        
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        
        # Use gemini-1.5-flash for faster candidate discovery
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    async def generate_json(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        """Generate JSON response. Schema is ignored in this simple impl."""
        import json
        
        # Prompt for JSON explicitly
        full_prompt = f"{prompt}\n\nRespond ONLY with valid JSON."
        
        response = self.model.generate_content(
            full_prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse LLM response as JSON: {response.text}") from e


def get_llm_adapter() -> LLMAdapter:
    """Factory to get the configured LLM adapter."""
    return GeminiAdapter()
