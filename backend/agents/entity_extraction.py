"""
Entity Extraction Agent - BioBERT-based NER

Extracts biomedical entities using BioBERT for NER.
Falls back to LLM for supplementary extraction.

Models are EXTRACTORS, not decision-makers.
BioBERT extracts structured facts; agents reason.
"""

from typing import List, Set
import re

from backend.agents.base_agent import BaseAgent
from backend.agents.schemas import (
    AgentState,
    BiomedicalEntity,
    EntityType,
    DrugRepurposingQuery,
    ExtractionMethod,
)


# Lazy imports for heavy dependencies
def _get_biobert_extractor():
    """Lazy load BioBERT extractor."""
    from backend.agents.biomedical_encoder import get_biobert_extractor
    return get_biobert_extractor()


def _get_llm_extractor():
    """Lazy load LLM extractor."""
    from backend.services.llm_service import extract_entities_with_llm
    return extract_entities_with_llm


class EntityExtractionAgent(BaseAgent):
    """
    Named Entity Recognition using BioBERT + LLM fallback.
    
    Extraction Strategy:
        1. BioBERT NER for drugs, diseases, genes
        2. LLM for supplementary entities BioBERT misses
        3. Merge and deduplicate
    
    Output: List[BiomedicalEntity] with model provenance
    """
    
    name = "entity_extraction_agent"
    description = "Extracts biomedical entities using BioBERT"
    version = "3.0.0"  # BioBERT integration
    
    required_input_keys = ["query"]
    output_keys = ["extracted_entities"]
    
    # Whether to use BioBERT (can disable if not available)
    USE_BIOBERT = True
    USE_LLM_FALLBACK = True
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Extract entities from query using BioBERT + LLM.
        """
        query: DrugRepurposingQuery = state["query"]
        text = query.raw_query
        
        entities: List[BiomedicalEntity] = []
        seen_names: Set[str] = set()
        
        # Stage 1: BioBERT extraction
        if self.USE_BIOBERT:
            biobert_entities = await self._extract_with_biobert(text)
            for entity in biobert_entities:
                if entity.name.lower() not in seen_names:
                    entities.append(entity)
                    seen_names.add(entity.name.lower())
        
        # Stage 2: LLM fallback for additional entities
        if self.USE_LLM_FALLBACK:
            llm_entities = await self._extract_with_llm(text)
            for entity in llm_entities:
                if entity.name.lower() not in seen_names:
                    entities.append(entity)
                    seen_names.add(entity.name.lower())
        
        state["extracted_entities"] = entities
        return state
    
    async def _extract_with_biobert(self, text: str) -> List[BiomedicalEntity]:
        """
        Extract entities using BioBERT NER.
        """
        entities = []
        
        try:
            extractor = _get_biobert_extractor()
            raw_entities = extractor.extract_entities(text)
            
            for raw in raw_entities:
                entity_type = self._map_type(raw.get("entity_type", ""))
                if entity_type is None:
                    continue
                
                name = raw.get("text", "").strip()
                if not name or len(name) < 2:
                    continue
                
                # Determine extraction method from model_used
                model_used = raw.get("model_used", "BioBERT")
                if model_used == "pattern":
                    extraction_method = ExtractionMethod.PATTERN
                else:
                    extraction_method = ExtractionMethod.BIOBERT
                
                entity = BiomedicalEntity(
                    id=f"{entity_type.value}:{name.lower().replace(' ', '_')}",
                    name=self._normalize_name(name, entity_type),
                    entity_type=entity_type,
                    aliases=[name.lower()],
                    extraction_method=extraction_method,
                    extraction_confidence=raw.get("confidence", 0.5),
                    metadata={
                        "char_start": raw.get("start", 0),
                        "char_end": raw.get("end", 0),
                    }
                )
                entities.append(entity)
        except Exception as e:
            # Fallback silently on BioBERT failure
            pass
        
        return entities
    
    async def _extract_with_llm(self, text: str) -> List[BiomedicalEntity]:
        """
        Extract entities using LLM (fallback/supplement).
        """
        entities = []
        
        try:
            extract_fn = _get_llm_extractor()
            llm_result = await extract_fn(text)
            
            # Process drugs
            for item in llm_result.get("drugs", []):
                entity = self._create_entity_from_llm(item, EntityType.DRUG)
                if entity:
                    entities.append(entity)
            
            # Process diseases
            for item in llm_result.get("diseases", []):
                entity = self._create_entity_from_llm(item, EntityType.DISEASE)
                if entity:
                    entities.append(entity)
            
            # Process genes
            for item in llm_result.get("genes", []):
                entity = self._create_entity_from_llm(item, EntityType.GENE)
                if entity:
                    entities.append(entity)
        except Exception:
            pass
        
        return entities
    
    def _create_entity_from_llm(
        self,
        data,
        entity_type: EntityType
    ) -> BiomedicalEntity | None:
        """Create entity from LLM output."""
        if isinstance(data, str):
            name = data.strip()
            entity_id = ""
        elif isinstance(data, dict):
            name = data.get("name", "").strip()
            entity_id = data.get("id", "")
        else:
            return None
        
        if not name or len(name) < 2:
            return None
        
        if not entity_id:
            entity_id = f"{entity_type.value}:{name.lower().replace(' ', '_')}"
        
        return BiomedicalEntity(
            id=entity_id,
            name=self._normalize_name(name, entity_type),
            entity_type=entity_type,
            aliases=[name.lower()],
            extraction_method=ExtractionMethod.LLM,
            extraction_confidence=0.7,  # Default LLM confidence
            metadata={"source": "llm_extraction"}
        )
    
    def _map_type(self, type_str: str) -> EntityType | None:
        """Map extracted type string to EntityType enum."""
        type_lower = type_str.lower()
        
        if type_lower in ("drug", "chemical", "compound"):
            return EntityType.DRUG
        elif type_lower in ("disease", "condition", "disorder"):
            return EntityType.DISEASE
        elif type_lower in ("gene", "protein"):
            return EntityType.GENE
        elif type_lower == "pathway":
            return EntityType.PATHWAY
        
        return None
    
    def _normalize_name(self, name: str, entity_type: EntityType) -> str:
        """Normalize entity name based on type."""
        name = name.strip()
        
        if entity_type == EntityType.GENE:
            # Genes are typically uppercase
            return name.upper()
        else:
            # Title case for drugs, diseases
            return name.title()
