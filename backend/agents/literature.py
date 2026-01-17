"""
BioMind Nexus - Literature Agent

Retrieves biomedical literature from PubMed.
Uses real NCBI E-utilities API for paper search.

Responsibilities:
- Search PubMed for relevant publications
- Extract citations and evidence from papers
- Generate structured EvidenceItem objects

Design: Pure function - receives entities, returns evidence.
API calls delegated to service layer.
"""

from typing import List, Dict, Any
import uuid
from datetime import datetime

from backend.agents.base_agent import BaseAgent
from backend.agents.schemas import (
    AgentState,
    BiomedicalEntity,
    EvidenceItem,
    EvidenceType,
    Citation,
    EntityType,
)
from backend.services.pubmed_service import (
    search_drug_disease_literature,
    search_entity_literature,
)


class LiteratureAgent(BaseAgent):
    """
    Agent for literature evidence retrieval from PubMed.
    
    This agent queries the NCBI PubMed database for relevant
    biomedical literature to support drug repurposing hypotheses.
    
    Pure Input: extracted_entities
    Pure Output: literature_evidence, literature_citations
    """
    
    name = "literature_agent"
    description = "Retrieves biomedical literature from PubMed"
    version = "2.0.0"  # Updated for real PubMed API
    
    required_input_keys = ["query", "extracted_entities"]
    output_keys = ["literature_evidence", "literature_citations"]
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Retrieve literature evidence from PubMed.
        
        Args:
            state: Contains 'extracted_entities' from EntityExtractionAgent
        
        Returns:
            State with 'literature_evidence' and 'literature_citations'
        """
        entities: List[BiomedicalEntity] = state["extracted_entities"]
        
        evidence_items: List[EvidenceItem] = []
        all_citations: List[Citation] = []
        
        # Identify drugs and diseases for targeted search
        drugs = [e for e in entities if e.entity_type == EntityType.DRUG]
        diseases = [e for e in entities if e.entity_type == EntityType.DISEASE]
        
        # Search for drug-disease combinations
        for drug in drugs:
            for disease in diseases:
                articles = await search_drug_disease_literature(
                    drug=drug.name,
                    disease=disease.name,
                    max_results=5
                )
                
                for article in articles:
                    citation = self._article_to_citation(article)
                    if citation:
                        all_citations.append(citation)
                        
                        evidence = self._create_evidence(
                            article=article,
                            citation=citation,
                            entities=[drug, disease]
                        )
                        if evidence:
                            evidence_items.append(evidence)
        
        # Search for individual entity literature if no combinations found
        if not evidence_items:
            for entity in entities[:3]:  # Limit to first 3 entities
                articles = await search_entity_literature(
                    entity_name=entity.name,
                    entity_type=entity.entity_type.value,
                    max_results=3
                )
                
                for article in articles:
                    citation = self._article_to_citation(article)
                    if citation:
                        all_citations.append(citation)
                        
                        evidence = self._create_evidence(
                            article=article,
                            citation=citation,
                            entities=[entity]
                        )
                        if evidence:
                            evidence_items.append(evidence)
        
        # Sort by confidence/relevance
        evidence_items.sort(key=lambda x: x.confidence, reverse=True)
        
        # Deduplicate citations
        seen_ids = set()
        unique_citations = []
        for c in all_citations:
            if c.source_id not in seen_ids:
                seen_ids.add(c.source_id)
                unique_citations.append(c)
        
        state["literature_evidence"] = evidence_items
        state["literature_citations"] = unique_citations
        
        return state
    
    def _article_to_citation(self, article: Dict[str, Any]) -> Citation | None:
        """Convert PubMed article dict to Citation model."""
        if not article:
            return None
        
        pmid = article.get("pmid", "")
        if not pmid:
            return None
        
        return Citation(
            source_type="pubmed",
            source_id=pmid,
            title=article.get("title", ""),
            authors=article.get("authors", []),
            year=article.get("year"),
            url=article.get("url", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"),
            excerpt=self._truncate_abstract(article.get("abstract", "")),
            relevance_score=article.get("relevance_score", 0.5)
        )
    
    def _truncate_abstract(self, abstract: str, max_length: int = 300) -> str:
        """Truncate abstract to excerpt length."""
        if not abstract:
            return ""
        if len(abstract) <= max_length:
            return abstract
        return abstract[:max_length].rsplit(" ", 1)[0] + "..."
    
    def _create_evidence(
        self,
        article: Dict[str, Any],
        citation: Citation,
        entities: List[BiomedicalEntity]
    ) -> EvidenceItem | None:
        """Create an EvidenceItem from a PubMed article."""
        if not article or not citation:
            return None
        
        abstract = article.get("abstract", "")
        title = article.get("title", "")
        
        # Use abstract as description, or title if no abstract
        description = abstract if abstract else title
        if not description:
            return None
        
        return EvidenceItem(
            evidence_id=f"lit_{citation.source_id}",
            evidence_type=EvidenceType.LITERATURE,
            description=self._truncate_abstract(description, 500),
            confidence=article.get("relevance_score", 0.5),
            citation=citation,
            entities_mentioned=entities
        )
