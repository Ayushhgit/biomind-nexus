"""
Integration test for the drug repurposing agent workflow with real APIs.

Requires:
- GROQ_API_KEY in backend/.env
- Internet connection for PubMed API
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import asyncio
import uuid
from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(os.path.join(project_root, "backend", ".env"))

from backend.agents import DrugRepurposingQuery, run_drug_repurposing_workflow
from backend.agents.schemas import BiomedicalEntity


async def main():
    # Check for API key
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in backend/.env")
        print("Please add: GROQ_API_KEY=your_api_key")
        return
    
    print(f"GROQ_API_KEY found: {api_key[:10]}...")
    
    # Test Case 1: Drug Repurposing Query (Should trigger ingestion)
    # Using a pair likely not in seed data
    query_text = "Can aspirin be repurposed to treat COVID-19?"
    
    print(f"\n🧪 Running Workflow Test with: '{query_text}'")
    
    try:
        # Create structured query manually to emulate extraction
        # (This helps the Orchestrator trigger ingestion immediately)
        query = DrugRepurposingQuery(
            query_id=f"test-{uuid.uuid4().hex[:6]}",
            raw_query=query_text,
            source_drug=BiomedicalEntity(id="drug:aspirin", name="Aspirin", entity_type="drug", extraction_method="manual", extraction_confidence=1.0),
            target_disease=BiomedicalEntity(id="disease:covid-19", name="COVID-19", entity_type="disease", extraction_method="manual", extraction_confidence=1.0),
            max_candidates=5
        )
        
        print("\n" + "="*60)
        print("Running drug repurposing workflow with Groq + PubMed APIs")
        print("="*60)
        print(f"Query: {query.raw_query}")
        print("-" * 60)
        
        result = await run_drug_repurposing_workflow(query, "user1", "req_test")
        
        print(f"\n✓ Workflow completed!")
        print(f"  Approved: {result.get('workflow_approved')}")
        print(f"  Steps: {' → '.join(result.get('step_history', []))}")
        
        # Entity extraction results
        entities = result.get('extracted_entities', [])
        print(f"\n📋 Extracted Entities ({len(entities)}):")
        for e in entities:
            print(f"   - {e.name} ({e.entity_type.value})")
        
        # Literature results
        evidence = result.get('literature_evidence', [])
        citations = result.get('literature_citations', [])
        print(f"\n📚 Literature Evidence ({len(evidence)} items, {len(citations)} citations):")
        for c in citations[:3]:
            print(f"   - [{c.source_id}] {c.title[:60]}...")
        
        # Drug candidates
        candidates = result.get('final_candidates', [])
        print(f"\n💊 Drug Candidates ({len(candidates)}):")
        for c in candidates:
            print(f"\n   [{c.rank}] {c.drug.name} → {c.target_disease.name}")
            print(f"       Score: {c.overall_score:.2f}, Confidence: {c.confidence:.2f}")
            print(f"       Hypothesis: {c.hypothesis[:100]}...")
            print(f"       Mechanism: {c.mechanism_summary[:100]}...")
        
        # Safety results
        safety = result.get('safety_result')
        if safety:
            print(f"\n🛡️ Safety Check:")
            print(f"   Passed: {safety.passed}")
            print(f"   Flags: {len(safety.flags)} total ({len(safety.critical_flags)} critical)")
            for flag in safety.flags[:3]:
                print(f"   - [{flag.severity.value}] {flag.message}")
        
        print("\n" + "="*60)
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


    finally:
        # Cleanup to avoid PyTorch segfaults
        from backend.agents.biomedical_encoder import cleanup_resources
        cleanup_resources()

if __name__ == "__main__":
    asyncio.run(main())
