"""
BioMind Nexus - Entity Extraction Agent

Extracts biomedical entities from natural language queries using Gemini LLM.
First step in the drug repurposing pipeline.

Responsibilities:
- Parse user query to identify drugs, diseases, genes
- Normalize entity names using LLM understanding
- Return structured BiomedicalEntity objects

Design: Pure function - receives query text, returns entities.
API calls delegated to service layer.
"""

from typing import List
import uuid

from backend.agents.base_agent import BaseAgent
from backend.agents.schemas import (
    AgentState,
    BiomedicalEntity,
    EntityType,
    DrugRepurposingQuery,
)
from backend.services.llm_service import extract_entities_with_llm


class EntityExtractionAgent(BaseAgent):
    """
    Agent for extracting biomedical entities from text using Gemini.
    
    This agent is the first step in the workflow, processing
    the raw query to identify key entities for downstream agents.
    
    Pure Input: DrugRepurposingQuery.raw_query
    Pure Output: List[BiomedicalEntity] in state["extracted_entities"]
    """
    
    name = "entity_extraction_agent"
    description = "Extracts drugs, diseases, and genes from query text using LLM"
    version = "2.0.0"  # Updated for LLM-based extraction
    
    # Required inputs
    required_input_keys = ["query"]
    
    # Generated outputs
    output_keys = ["extracted_entities"]
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Extract biomedical entities from the query using Gemini.
        
        Args:
            state: Must contain 'query' (DrugRepurposingQuery)
        
        Returns:
            State with 'extracted_entities' populated
        """
        query: DrugRepurposingQuery = state["query"]
        
        # Call Gemini service for entity extraction
        llm_result = await extract_entities_with_llm(query.raw_query)
        
        entities: List[BiomedicalEntity] = []
        
        # Process drugs
        for drug_data in llm_result.get("drugs", []):
            entity = self._create_entity(drug_data, EntityType.DRUG)
            if entity and entity not in entities:
                entities.append(entity)
        
        # Process diseases
        for disease_data in llm_result.get("diseases", []):
            entity = self._create_entity(disease_data, EntityType.DISEASE)
            if entity and entity not in entities:
                entities.append(entity)
        
        # Process genes
        for gene_data in llm_result.get("genes", []):
            entity = self._create_entity(gene_data, EntityType.GENE)
            if entity and entity not in entities:
                entities.append(entity)
        
        state["extracted_entities"] = entities
        
        return state
    
    def _create_entity(self, data: dict, entity_type: EntityType) -> BiomedicalEntity | None:
        """
        Create a BiomedicalEntity from LLM extraction result.
        
        Args:
            data: Dict with 'name' and optional 'id'
            entity_type: Type of entity
        
        Returns:
            BiomedicalEntity or None if invalid
        """
        if isinstance(data, str):
            # Handle case where LLM returns just a string
            name = data.strip()
            entity_id = ""
        elif isinstance(data, dict):
            name = data.get("name", "").strip()
            entity_id = data.get("id", "")
        else:
            return None
        
        if not name:
            return None
        
        # Generate ID if not provided
        if not entity_id:
            entity_id = f"{entity_type.value}:{name.lower().replace(' ', '_')}"
        
        # Normalize name
        normalized_name = name.title()
        if entity_type == EntityType.GENE:
            normalized_name = name.upper()
        
        return BiomedicalEntity(
            id=entity_id,
            name=normalized_name,
            entity_type=entity_type,
            aliases=[name.lower()],
            metadata={"extraction_method": "gemini_llm"}
        )
