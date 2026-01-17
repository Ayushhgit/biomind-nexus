"""
BioMind Nexus - LLM Service (Groq)

Service layer for Groq API interactions using OpenAI-compatible interface.
This module handles all LLM calls and keeps API logic out of agents.

Design: Agents call this service; they don't manage API keys or connections.
"""

import os
import json
from typing import Optional, Dict, Any, List

from groq import Groq

from backend.config import settings


# Initialize client lazily
_client = None


def _get_client() -> Groq:
    """Get or create the Groq client."""
    global _client
    if _client is None:
        api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment")
        _client = Groq(api_key=api_key)
    return _client


def _call_llm(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Make a call to the Groq LLM."""
    client = _get_client()
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=2000,
    )
    
    return response.choices[0].message.content


async def extract_entities_with_llm(query: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Use Groq LLM to extract biomedical entities from text.
    
    Args:
        query: Natural language query text
    
    Returns:
        Dict with 'drugs', 'diseases', 'genes' lists
    """
    system_prompt = "You are a biomedical entity extraction system. Extract entities and return ONLY valid JSON."
    
    prompt = f"""Extract biomedical entities from the following query.
Return a JSON object with these keys:
- "drugs": list of drug/compound names found
- "diseases": list of disease/condition names found  
- "genes": list of gene/protein names found

Each item should be an object with "name" and "id" (use standard identifiers like DrugBank IDs, DOID, HGNC symbols when known, otherwise leave id empty).

Query: "{query}"

Return ONLY valid JSON, no markdown or explanation."""

    try:
        text = _call_llm(prompt, system_prompt)
        
        # Clean up potential markdown formatting
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text)
    except Exception as e:
        print(f"Entity extraction error: {e}")
        return {"drugs": [], "diseases": [], "genes": []}


async def generate_hypothesis_with_llm(
    drug: str,
    disease: str,
    evidence_summaries: List[str],
    mechanism_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use Groq LLM to generate a drug repurposing hypothesis.
    
    Args:
        drug: Drug name
        disease: Target disease
        evidence_summaries: List of supporting evidence excerpts
        mechanism_context: Optional known mechanism info
    
    Returns:
        Dict with 'hypothesis', 'mechanism_summary', 'confidence'
    """
    system_prompt = "You are a biomedical research assistant specializing in drug repurposing. Return ONLY valid JSON."
    
    evidence_text = "\n".join(f"- {e}" for e in evidence_summaries[:5])
    
    prompt = f"""Generate a drug repurposing hypothesis.

Drug: {drug}
Target Disease: {disease}

Supporting Evidence:
{evidence_text if evidence_text else "- No specific evidence provided"}

{f"Known Mechanism Context: {mechanism_context}" if mechanism_context else ""}

Return a JSON object with:
- "hypothesis": A clear statement of how this drug could treat the disease (1-2 sentences)
- "mechanism_summary": Explanation of the proposed mechanism of action (2-3 sentences)
- "confidence": A number between 0.0 and 1.0 indicating confidence based on evidence strength
- "key_pathways": List of biological pathways involved

Return ONLY valid JSON, no markdown or explanation."""

    try:
        text = _call_llm(prompt, system_prompt)
        
        # Clean up potential markdown formatting
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        result = json.loads(text)
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
        return result
    except Exception as e:
        print(f"Hypothesis generation error: {e}")
        return {
            "hypothesis": f"{drug} may have therapeutic potential for {disease}.",
            "mechanism_summary": "Unable to generate detailed mechanism. Manual review recommended.",
            "confidence": 0.3,
            "key_pathways": []
        }


async def analyze_mechanism_paths_with_llm(
    drug: str,
    disease: str,
    pathway_nodes: List[str]
) -> Dict[str, Any]:
    """
    Use Groq LLM to analyze and explain a mechanistic pathway.
    
    Args:
        drug: Source drug
        disease: Target disease
        pathway_nodes: Intermediate nodes in the pathway
    
    Returns:
        Dict with pathway analysis
    """
    system_prompt = "You are a biomedical pathway analyst. Return ONLY valid JSON."
    
    pathway_str = " → ".join([drug] + pathway_nodes + [disease])
    
    prompt = f"""Analyze this potential drug-disease mechanistic pathway:

Pathway: {pathway_str}

Return a JSON object with:
- "plausibility_score": Number between 0.0 and 1.0
- "explanation": Brief scientific explanation of how this pathway could work
- "edge_types": List of relationship types between consecutive nodes (e.g., "inhibits", "activates", "modulates")
- "supporting_evidence_needed": What evidence would strengthen this hypothesis

Return ONLY valid JSON, no markdown or explanation."""

    try:
        text = _call_llm(prompt, system_prompt)
        
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text)
    except Exception as e:
        print(f"Mechanism analysis error: {e}")
        return {
            "plausibility_score": 0.5,
            "explanation": "Analysis unavailable.",
            "edge_types": ["relates_to"] * (len(pathway_nodes) + 1),
            "supporting_evidence_needed": []
        }
