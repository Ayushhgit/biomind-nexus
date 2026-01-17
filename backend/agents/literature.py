"""
Literature Agent.

This agent searches PubMed for papers.
We use PubMedBERT to see if the papers are actually about what we want.
"""

from typing import List, Dict, Any

from backend.agents.base_agent import BaseAgent
from backend.agents.schemas import (
    AgentState,
    BiomedicalEntity,
    EvidenceItem,
    EvidenceType,
    Citation,
    EntityType,
    ExtractionMethod,
)
from backend.services.pubmed_service import (
    search_drug_disease_literature,
    search_entity_literature,
)


# Lazy import for PubMedBERT scorer
def _get_pubmedbert_scorer():
    """Load the scorer model if we can."""
    try:
        from backend.agents.biomedical_encoder import get_pubmedbert_scorer
        return get_pubmedbert_scorer()
    except ImportError:
        return None


class LiteratureAgent(BaseAgent):
    """
    Finds papers and scores them.
    
    Plan:
    1. Search PubMed
    2. Score the papers with PubMedBERT
    3. Make evidence items with confidence scores
    """
    
    name = "literature_agent"
    description = "Retrieves literature and scores evidence with PubMedBERT"
    version = "3.0.0"  # PubMedBERT integration
    
    required_input_keys = ["query", "extracted_entities"]
    output_keys = ["literature_evidence", "literature_citations"]
    
    # Whether to use PubMedBERT for scoring
    USE_PUBMEDBERT = True
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Main function to get papers and score them.
        """
        entities: List[BiomedicalEntity] = state["extracted_entities"]
        
        evidence_items: List[EvidenceItem] = []
        all_citations: List[Citation] = []
        
        # Get scorer (may fail if transformers not installed)
        scorer = None
        if self.USE_PUBMEDBERT:
            scorer = _get_pubmedbert_scorer()
        
        # Identify drugs and diseases
        drugs = [e for e in entities if e.entity_type == EntityType.DRUG]
        diseases = [e for e in entities if e.entity_type == EntityType.DISEASE]
        genes = [e for e in entities if e.entity_type in (EntityType.GENE, EntityType.PROTEIN)]
        
        # Search for drug-disease literature
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
                        
                        # Score with PubMedBERT if available
                        evidence = self._create_evidence(
                            article=article,
                            citation=citation,
                            entities=[drug, disease],
                            scorer=scorer,
                            drug_name=drug.name,
                            disease_name=disease.name
                        )
                        if evidence:
                            evidence_items.append(evidence)
        
        # Search individual entities if no combinations
        if not evidence_items:
            for entity in entities[:3]:
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
                            entities=[entity],
                            scorer=scorer
                        )
                        if evidence:
                            evidence_items.append(evidence)
        
        # Sort by confidence
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
        """Turn the dictionary into a Citation object."""
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
            excerpt=self._truncate(article.get("abstract", ""), 300),
            relevance_score=article.get("relevance_score", 0.5)
        )
    
    def _create_evidence(
        self,
        article: Dict[str, Any],
        citation: Citation,
        entities: List[BiomedicalEntity],
        scorer=None,
        drug_name: str = "",
        disease_name: str = ""
    ) -> EvidenceItem | None:
        """Make an evidence object and score it."""
        if not article or not citation:
            return None
        
        abstract = article.get("abstract", "")
        title = article.get("title", "")
        description = abstract if abstract else title
        
        if not description:
            return None
        
        # Base confidence from keyword matching
        base_confidence = article.get("relevance_score", 0.5)
        
        # PubMedBERT scoring
        model_used = None
        if scorer and drug_name and disease_name:
            try:
                # Score drug-disease relation using PubMedBERT
                relation_scores = scorer.score_relation(
                    drug=drug_name,
                    target="",  # No specific target
                    disease=disease_name,
                    context=description[:512]
                )
                
                # Use PubMedBERT score
                pubmedbert_score = relation_scores.get("overall_score", 0.5)
                
                # Blend base confidence with PubMedBERT score
                final_confidence = (base_confidence * 0.4) + (pubmedbert_score * 0.6)
                model_used = ExtractionMethod.PUBMEDBERT
            except Exception:
                final_confidence = base_confidence
                model_used = ExtractionMethod.PATTERN
        else:
            final_confidence = base_confidence
            model_used = ExtractionMethod.PATTERN
        
        return EvidenceItem(
            evidence_id=f"lit_{citation.source_id}",
            evidence_type=EvidenceType.LITERATURE,
            description=self._truncate(description, 500),
            confidence=min(1.0, max(0.0, final_confidence)),
            citation=citation,
            entities_mentioned=entities
        )
    
    def _truncate(self, text: str, max_len: int = 300) -> str:
        """Shorten text if it's too long."""
        if not text:
            return ""
        if len(text) <= max_len:
            return text
        return text[:max_len].rsplit(" ", 1)[0] + "..."
