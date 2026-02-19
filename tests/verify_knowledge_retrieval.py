import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import memory

def verify_knowledge():
    print("--- Verifying Knowledge Base Retrieval ---")
    
    # Force localized provider to match seed script
    memory.maker.provider = "local"
    # Ensure no remote config interferes
    memory.maker.config["embedding_provider"] = "local"
    
    # 1. Test Retrieval of Tool Guide
    query = "How do I create a new tool?"
    print(f"Query: {query}")
    try:
        # Give it a moment if model needs loading
        result = memory.recall_instructions(query)
        
        if result:
            print(f"✅ Found {len(result)} chars of instructions.")
            if "Tool Creation" in result or "create_tool" in result:
                print("✅ Content matches expected 'Tool Creation' guide.")
                print("Snippet:", result[:200].replace("\n", " "))
            else:
                print("⚠️  Content does not seem to match 'Tool Creation' guide.")
                print("Got:", result[:200])
        else:
            print("❌ No instructions found. (Database might be empty or embeddings mismatch)")
            
    except Exception as e:
        print(f"❌ Error during recall: {e}")

    # 3. Test Environments
    print("\nQuery: How do I manage environments?")
    try:
        result = memory.recall_instructions("How do I manage environments?")
        if result and ("env_manager.py" in result or "Venv" in result):
            print("✅ Environment guide retrieved.")
        else:
             print("⚠️  Environment guide NOT retrieved.")
    except:
        pass

    # 4. Test Lifecycle/Security
    print("\nQuery: What are my permissions?")
    try:
        result = memory.recall_instructions("What are my permissions?")
        if result and ("config.json" in result or "verify_context.py" in result):
            print("✅ Security guide retrieved.")
        else:
             print("⚠️  Security guide NOT retrieved.")
    except:
        pass

if __name__ == "__main__":
    verify_knowledge()
