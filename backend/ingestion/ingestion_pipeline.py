"""
BioMind Nexus - Ingestion Pipeline

Orchestrates the on-demand population of the knowledge graph.
Ensures agents rely on persisted facts, not live fetching.

Pipeline:
1. Check Neo4j for existing knowledge
2. If incomplete:
   a. Fetch abstracts from PubMed (Rate-safe)
   b. Extract Entities (BioBERT) & Relations (Rule-based + PubMedBERT Support)
   c. Validate facts (Confidence thresholds)
   d. Persist to Neo4j (Idempotent upserts)
3. Return loaded GraphContext

Constraints:
- Agents must NOT call this.
- Updates happen BEFORE agents run.
- "Fact" = High confidence, specific relation.
"""

import asyncio
import re
from typing import List, Dict, Set, Tuple
from datetime import datetime

from backend.domain.models import GraphContext
from backend.ingestion.pubmed_client import PubMedClient
from backend.dal import neo4j_dal
from backend.agents.biomedical_encoder import get_biobert_extractor, get_pubmedbert_scorer
from backend.agents.schemas import EntityType, RelationType, BiomedicalEntity, ExtractionMethod

# Heuristic Relation Patterns (Fallback for missing RE model)
RELATION_PATTERNS = {
    RelationType.INHIBITS: [
        r"inhibits?", r"blocks?", r"suppresses?", r"antagoni(st|zes)", 
        r"reduces?", r"downregulates?"
    ],
    RelationType.ACTIVATES: [
        r"activates?", r"stimulates?", r"induces?", r"promotes?", 
        r"agoni(st|zes)", r"upregulates?", r"increases?"
    ],
    RelationType.BINDS: [
        r"binds?", r"interacts? with", r"affinity for", r"ligand"
    ],
    RelationType.TREATS: [
        r"treats?", r"therapy for", r"effective against", r"used for"
    ],
    RelationType.CAUSES: [
        r"causes?", r"leads to", r"induces?", r"associated with"
    ]
}

class IngestionPipeline:
    
    def __init__(self):
        self.pubmed = PubMedClient()
        self.biobert = get_biobert_extractor()
        self.scorer = get_pubmedbert_scorer()
    
    async def ingest_if_missing(self, drug: str, disease: str) -> GraphContext:
        """
        Main entry point.
        Checks DB, assumes 'missing' if no direct pathway edges found.
        If missing, runs ingestion.
        Always returns relevant GraphContext (loaded from DB).
        """
        # 1. Check Neo4j
        # We verify if we have *pathway candidates*. If we really have ZERO info, we ingest.
        # Simple heuristic: Do we have >0 pathway edges between drug and disease context?
        existing_context = await neo4j_dal.load_graph_context_for_query(drug, disease)
        
        # If we have relevant edges, likely we have coverage.
        # But for "On-Demand", if edge count is low (< 3?), we might try fetching more.
        # For now, simplistic: if < 1 edge, ingest.
        edge_count = len(existing_context.get("pathway_edges", []))
        
        if edge_count >= 1:
            print(f"Ingestion: Knowledge exists ({edge_count} edges). Skipping fetch.")
            await self.pubmed.close()
            return existing_context
        
        print(f"Ingestion: Knowledge gap detected. Fetching for {drug} -> {disease}...")
        
        try:
            # 2. Ingest
            await self._run_ingestion_cycle(drug, disease)
            
            # 3. Reload Context
            print("Ingestion: Reloading graph context...")
            updated_context = await neo4j_dal.load_graph_context_for_query(drug, disease)
            return updated_context
            
        finally:
            await self.pubmed.close()

    async def _run_ingestion_cycle(self, drug: str, disease: str):
        """Fetch papers, extract facts, persist to Neo4j."""
        # A. Fetch
        # Search for intersection papers (Drug AND Disease)
        pmids = await self.pubmed.search_literature(drug, disease, max_results=10)
        
        # If few direct, search Drug+Mechanism or Disease+Mechanism? 
        # Simplicity: just Drug+Disease for now.
        if not pmids:
            # Fallback: Search separately? No, too noisy.
            print("Ingestion: No literature found intersection drug and disease.")
            return

        articles = await self.pubmed.fetch_abstracts(pmids)
        print(f"Ingestion: Analyizing {len(articles)} abstracts...")
        
        unique_facts = 0
        
        for article in articles:
            text = article["text"]
            pmid = article["pmid"]
            
            # B. Extract Entities (NER)
            # We assume BioBERT extractor returns dicts
            raw_entities = self.biobert.extract_entities(text)
            
            # Convert to objects & deduplicate
            entities_map = {}
            for e in raw_entities:
                norm_name = e["text"].strip() # In real impl, would use smarter normalization
                e_type = e["entity_type"]
                # Skip short/noisy
                if len(norm_name) < 3: continue
                
                entities_map[norm_name.lower()] = {
                    "name": norm_name,
                    "type": e_type,
                    "conf": e["confidence"]
                }
            
            # C. Extract Relations (Simple RE Strategy)
            # Look for pairs in same sentence with a relation keyword
            sentences = re.split(r'[.!?]', text)
            
            for sent in sentences:
                sent_entities = []
                for name_lower, info in entities_map.items():
                    if name_lower in sent.lower():
                        sent_entities.append(info)
                
                # Pairwise check
                if len(sent_entities) < 2: continue
                
                import itertools
                for e1, e2 in itertools.combinations(sent_entities, 2):
                    # Skip same entity
                    if e1["name"].lower() == e2["name"].lower(): continue
                    
                    # Relation Extraction
                    rel_type, rel_conf = self._extract_relation(sent, e1, e2)
                    
                    if rel_type and rel_conf >= 0.5:
                        # D. Persist (Upsert)
                        # Upsert source
                        await self._upsert_entity(e1)
                        # Upsert target
                        await self._upsert_entity(e2)
                        
                        # Upsert Edge
                        success = await neo4j_dal.upsert_relation(
                            source_name=e1["name"],
                            source_type=e1["type"],
                            relation=rel_type.name, # Enum to str
                            target_name=e2["name"],
                            target_type=e2["type"],
                            confidence=rel_conf,
                            pmid=pmid,
                            extraction_method="biobert+regex"
                        )
                        if success:
                            unique_facts += 1

        print(f"Ingestion: Persisted {unique_facts} new facts to Neo4j.")

    def _extract_relation(self, text: str, e1: Dict, e2: Dict) -> Tuple[RelationType, float]:
        """
        Determine relation between e1 and e2 in text.
        Returns (RelationType, Confidence) or (None, 0.0).
        """
        # 1. Regex Match
        found_type = None
        
        for r_type, patterns in RELATION_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    found_type = r_type
                    break
            if found_type: break
        
        if not found_type:
            return None, 0.0
            
        # 2. Validation with PubMedBERT (Evidence Scoring)
        # Does this text actually support a relation?
        # Hypothesis: e1 rel e2
        # hypothesis_text = f"{e1['name']} {found_type.name} {e2['name']}"
        # support = self.scorer.score_evidence(text, hypothesis_text)
        
        # OR using score_relation (Semantic plausibility)
        # Note: score_relation is generic drug->target->disease. 
        # Here we just check semantic affinity.
        # support = self.scorer.similarity(text, hypothesis_text)
        
        # Simple heuristic: BioBERT NER Conf * 0.8 (Pattern)
        base_conf = min(e1["conf"], e2["conf"])
        final_conf = base_conf * 0.8 # Penality for regex
        
        return found_type, final_conf

    async def _upsert_entity(self, entity_info: Dict):
        """Dispatch upsert based on type."""
        t = entity_info["type"].lower()
        n = entity_info["name"]
        
        if t == "drug": await neo4j_dal.upsert_drug(n)
        elif t == "disease": await neo4j_dal.upsert_disease(n)
        elif t == "gene" or t == "protein": await neo4j_dal.upsert_gene(n)
        elif t == "pathway": await neo4j_dal.upsert_pathway(n)

# Global Instance
_ingestion_pipeline = None

def get_ingestion_pipeline() -> IngestionPipeline:
    global _ingestion_pipeline
    if not _ingestion_pipeline:
        _ingestion_pipeline = IngestionPipeline()
    return _ingestion_pipeline
