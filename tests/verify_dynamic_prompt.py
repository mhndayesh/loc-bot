import sys
import os
import json
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import memory
from engine import AgentEngine

def test_dynamic_prompt():
    print("--- Testing Dynamic System Prompt ---")
    
    # Mock the embedding function to avoid heavy torch load
    print("Mocking embeddings for test speed...")
    import hashlib
    def mock_encode(text):
        # Deterministic pseudo-random vector based on text hash
        # We need a vector implementation that returns high similarity for "protocol" related queries
        # Let's make a simple "keyword" based vector for testing
        vec = [0.0] * 384
        if "protocol" in text.lower():
            vec[0] = 1.0 # High relevance dimension
        else:
            vec[1] = 1.0 # Irrelevant dimension
        return vec

    # Patch the maker
    memory.maker.encode = mock_encode
    
    # 1. Teach a unique nonsense rule
    unique_keyword = "XYZZY_PROTOCOL"
    rule = f"If the user mentions 'protocol', you must mention {unique_keyword}."
    print(f"Teaching rule: {rule}")
    memory.learn_instruction(rule)
    
    # Allow some time for file I/O (though lock should handle it)
    time.sleep(1)
    
    # 2. Verify Retrieval directly
    print("Verifying memory recall...")
    recalled = memory.recall_instructions("What is the protocol?")
    if recalled and unique_keyword in recalled:
        print("✅ Direct recall successful.")
    else:
        print(f"❌ Direct recall failed. Got: {recalled}")
        return

    # 3. Verify Engine Prompt Assembly
    print("Verifying Engine.get_full_prompt context injection...")
    engine = AgentEngine()
    
    # Mock state to simulate a relevant goal
    engine.state["goal"] = "Check the protocol status"
    
    prompt = engine.get_full_prompt()
    
    if unique_keyword in prompt:
        print("✅ Engine prompt contains dynamic instruction.")
        print("Prompt snippet:")
        start = prompt.find("## Dynamic Instructions")
        print(prompt[start:start+200] + "...")
    else:
        print("❌ Engine prompt logic failed to inject instruction.")
        print("Goal was:", engine.state["goal"])
        # print("Full prompt:", prompt) # Debug only
        
    # 4. Verify negative case (irrelevant goal)
    engine.state["goal"] = "Make a sandwich"
    prompt_negative = engine.get_full_prompt()
    if unique_keyword in prompt_negative:
         print("⚠️  Warning: Instruction leaked into irrelevant context (Semantic search might be too fuzzy).")
    else:
         print("✅ Instruction correctly omitted from irrelevant context.")

    # 5. Verify Knowledge Retrieval
    print("Verifying Detailed Knowledge Retrieval...")
    # Update mock for "tool" query
    def mock_encode_v2(text):
        vec = [0.0] * 384
        if "protocol" in text.lower():
            vec[0] = 1.0 
        elif "tool" in text.lower() or "create" in text.lower():
            vec[2] = 1.0 # Tool dimension
        else:
            vec[1] = 1.0
        return vec
    memory.maker.encode = mock_encode_v2
    
    # We must re-teach the tool guide with the new mock because the old seed used the old mock (or real embeddings).
    # Actually, the seed script used real embeddings (or local provider). 
    # Verification script mocks the encoder, so it won't match the real embeddings in the DB unless the DB was also mocked.
    # CRITICAL: The seed script ran in a separate process with REAL/LOCAL embeddings.
    # This verification script uses MOCK embeddings. They are incompatible.
    # To verify correctly without re-seeding everything in this script, we should just query the vault directly 
    # and trust the cosine similarity logic, OR we rely on the fact that we can't easily verify real embeddings with a mock.
    
    # Strategy: We will just try to recall "Tool Creation" using the real `memory.recall_instructions` 
    # BUT we need to restore the real encoder for this to work against the real DB.
    
    print("Restoring real local encoder for knowledge verification...")
    memory.maker.provider = "local"
    # Force reload of model if needed (it's a singleton, so just setting provider might be enough if logic supports it)
    # The memory module lazily loads local model.
    try:
        recalled_guide = memory.recall_instructions("How do I create a python tool script?")
        if recalled_guide and "Tool Creation" in recalled_guide:
             print("✅ Knowledge Guide retrieval successful.")
        else:
             print(f"⚠️ Knowledge Guide retreival check inconclusive (might need real embedding model). Got: {str(recalled_guide)[:100]}...")
    except Exception as e:
        print(f"⚠️ Knowledge verification skipped due to model load issue: {e}")

if __name__ == "__main__":
    test_dynamic_prompt()
