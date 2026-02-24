import os
import sys
import time
import uuid
import logging

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.core import memory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory_convo_test")

def run_convo_test():
    logger.info("Starting Long Conversational Test...")
    
    # 1. Simulate a long conversation
    dialogue = [
        ("User", "Hey, I'm planning a deep-sea exploration mission to the Mariana Trench."),
        ("Agent", "That sounds fascinating! What are your primary objectives?"),
        ("User", "We want to find the rare 'Glow-Fin Shark' that lives exactly at 10,994 meters deep."),
        ("Agent", "The Glow-Fin Shark? I'll make a note of that depth: 10,994 meters."),
        ("User", "Also, the mission lead is Dr. Elena Vance, and our submersible is named 'The Abyss-Walker'."),
        ("Agent", "Dr. Elena Vance and The Abyss-Walker. Got it. What's the budget?"),
        ("User", "The budget is 15.5 million dollars. We start on July 14th, 2026."),
        ("Agent", "July 14th, 2026. $15.5M. I've logged the mission details.")
    ]
    
    logger.info("Phase 1: Ingesting initial mission planning dialogue...")
    group_id = str(uuid.uuid4())
    for i, (speaker, text) in enumerate(dialogue):
        memory.memorize(f"{speaker}: {text}", metadata={
            "type": "CONVO", 
            "group_id": group_id, 
            "chunk_index": i
        })
    
    # 2. Add "noise" turns (unrelated conversation)
    logger.info("Phase 2: Adding noise turns (unrelated topics)...")
    noise = [
        "User: Can you tell me a joke about robots?",
        "Agent: Why did the robot go to the doctor? Because it had a virus!",
        "User: What's the weather like in Tokyo right now?",
        "Agent: Currently, it's 18 degrees and rainy in Tokyo.",
        "User: I'm thinking of getting a new laptop. Maybe a MacBook?",
        "Agent: MacBooks are great for design, but consider a ThinkPad if you need durability."
    ]
    for i, text in enumerate(noise):
        memory.memorize(text, metadata={
            "type": "CONVO", 
            "noise": True,
            "chunk_index": i + len(dialogue)
        })

    # 3. Test multi-turn recall (specific detail from the beginning)
    logger.info("Phase 3: Testing recall of specific mission details...")
    
    questions = [
        ("Who is leading the Mariana Trench mission?", "Dr. Elena Vance"),
        ("What is the name of the submersible?", "The Abyss-Walker"),
        ("What is the exact depth where the Glow-Fin Shark is found?", "10,994 meters"),
        ("When does the mission start?", "July 14th"),
        ("What's the budget for the expedition?", "15.5 million")
    ]
    
    success_count = 0
    for q, expected in questions:
        logger.info(f"Question: {q}")
        start = time.perf_counter()
        result = memory.recall(q)
        elapsed = time.perf_counter() - start
        
        if expected.lower() in str(result).lower():
            logger.info(f"✅ SUCCESS: Found '{expected}' in {elapsed:.2f}s")
            success_count += 1
        else:
            logger.error(f"❌ FAILURE: Result did not contain '{expected}'. Result: {result}")

    # 4. Long Context Reassembly Test (Group Recall)
    logger.info("Phase 4: Testing full session reconstruction (Group Recall)...")
    start = time.perf_counter()
    full_history = memory.get_by_group(group_id)
    elapsed = time.perf_counter() - start
    
    if len(full_history) == len(dialogue):
        logger.info(f"✅ SUCCESS: Reconstructed all {len(dialogue)} turns of the primary thread in {elapsed:.4f}s")
    else:
        logger.error(f"❌ FAILURE: Reconstructed only {len(full_history)}/{len(dialogue)} turns.")

    # Summary
    logger.info("════════════════════════════════════")
    logger.info("CONVERSATIONAL TEST SUMMARY")
    logger.info(f"Recall Accuracy: {success_count}/{len(questions)}")
    logger.info(f"Session Reassembly: {'Passed' if len(full_history) == len(dialogue) else 'Failed'}")
    logger.info("════════════════════════════════════")

if __name__ == "__main__":
    run_convo_test()
