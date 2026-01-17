
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.biomedical_encoder import get_biobert_extractor

def test_biobert():
    print("Loading BioBERT Extractor...")
    try:
        extractor = get_biobert_extractor()
        text = "Aspirin inhibits COX-2 and is used to treat headache."
        print(f"Text: {text}")
        
        entities = extractor.extract_entities(text)
        print("\nExtracted Entities:")
        for e in entities:
            print(f"- {e}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_biobert()
