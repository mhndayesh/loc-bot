import os
import sys
import time
import shutil

# Add project root to path
sys.path.append(os.getcwd())

from engine import AgentEngine
import memory

def test_deja_vu():
    print("=== VECTOR MEMORY TEST: DEJA VU ===")
    
    # 1. Cleanup old DB for clean test
    if os.path.exists("memory_db"):
        print("Cleaning old memory_db...")
        # Chromadb client might hold lock, but we'll try
        try:
            shutil.rmtree("memory_db")
        except:
            print("Warning: Could not delete memory_db (locked?). Continuing...")

    engine = AgentEngine()
    
    # 2. Simulate a task success
    problem = "How to sort a list in Python?"
    solution = "Use the .sort() method or sorted() function."
    print(f"Feeding memory: {problem}")
    memory.memorize(problem, solution, rating=5)
    
    # Wait for potential IO
    time.sleep(1)
    
    # 3. Request similar task
    print("\nRequesting similar task: 'I need to order some items in a python array'")
    wisdom = memory.recall("I need to order some items in a python array")
    
    if wisdom:
        print(f"SUCCESS: Memory recalled!\nWisdom: {wisdom}")
    else:
        print("FAILURE: Memory not recalled.")
        
    # 4. Check prompt injection
    engine.state['goal'] = "Order python items"
    prompt = engine.get_full_prompt()
    # We call pulse() to see if it logs the injection
    print("\nChecking engine pulse injection...")
    # Mocking call_llm to avoid real API call
    engine.call_llm = lambda p, u="", i=None: "[THINK] I remember the list sorting solution. [/THINK] [TOOL] update_state('done', 'completed') [/TOOL]"
    
    engine.pulse()
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    test_deja_vu()
