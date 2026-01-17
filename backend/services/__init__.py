"""
BioMind Nexus - Services Package

Service layer for external API integrations.
Agents use these services; they don't manage API connections directly.
"""

from backend.services.llm_service import (
    extract_entities_with_llm,
    generate_hypothesis_with_llm,
    analyze_mechanism_paths_with_llm,
)

from backend.services.pubmed_service import (
    search_pubmed,
    fetch_pubmed_articles,
    search_drug_disease_literature,
    search_entity_literature,
)


__all__ = [
    # LLM Service
    "extract_entities_with_llm",
    "generate_hypothesis_with_llm",
    "analyze_mechanism_paths_with_llm",
    
    # PubMed Service
    "search_pubmed",
    "fetch_pubmed_articles",
    "search_drug_disease_literature",
    "search_entity_literature",
]
