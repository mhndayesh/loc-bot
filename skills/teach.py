"""
teach: Add a new permanent instruction to the agent's dynamic system prompt.
Usage: teach("When writing Python, always use type hints.")
"""
import sys
import os

# Add parent directory to path to import memory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import memory

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: teach \"Your instruction here\"")
        sys.exit(1)
        
    instruction = " ".join(sys.argv[1:])
    
    try:
        mem_id = memory.learn_instruction(instruction)
        if mem_id:
            print(f"OK: Instruction learned (ID: {mem_id}). I will remember this when relevant.")
        else:
            print("Error: Failed to save instruction.")
    except Exception as e:
        print(f"Error: {e}")
