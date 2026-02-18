import os
import sys
import json
import time

# Add project root to path
sys.path.append(os.getcwd())

from engine import AgentEngine

def simulate():
    print("=== HUMAN SIMULATION: START ===")
    
    # Initialize Engine
    engine = AgentEngine()
    
    # 1. Simulate Human giving a task
    goal = "Check system stats and save a summary to 'audit_report.txt'"
    engine.state['goal'] = goal
    engine.state['status'] = 'ready'
    engine.save_state()
    print(f"Human: {goal}")

    # --- SIMULATION LOOP ---
    # We will simulate the LLM's responses as if it were following the Map-Based Architecture
    
    scenarios = [
        # Turn 1: Orientation
        {
            "thought": "I am mo the bot. My prompt is lean. I must read MAP.md to orient myself.",
            "tool": 'read_file("MAP.md")'
        },
        # Turn 2: Skill Discovery
        {
            "thought": "MAP.md points to SKILLS.md for tools. I need to find a way to get system stats.",
            "tool": 'read_file("SKILLS.md")'
        },
        # Turn 3: Action - Get Stats
        {
            "thought": "SKILLS.md lists system_stats.py. I will execute it to gather data.",
            "tool": 'run_command("python skills/system_stats.py")'
        },
        # Turn 4: Action - Write Report
        {
            "thought": "I have the stats. Now I will write the summary to audit_report.txt.",
            "tool": 'write_file("audit_report.txt", "System Audit Summary:\\nCPU: OK\\nRAM: OK\\nDisk: OK")'
        },
        # Turn 5: Completion
        {
            "thought": "Task complete. I have saved the report. I will update my status.",
            "tool": 'update_state("Check system stats and save summary", "completed")'
        }
    ]

    for i, step in enumerate(scenarios):
        print(f"\n--- TURN {i+1} ---")
        prompt = engine.get_full_prompt()
        print(f"System Prompt Length: {len(prompt)} characters")
        
        # Simulate LLM Response
        response = f"[THINK]\n{step['thought']}\n[/THINK]\n\n[TOOL] {step['tool']} [/TOOL]"
        print(f"Bot Output: {response}")
        
        # Parse and Run
        result = engine.parse_and_run(response)
        print(f"Tool Result: {str(result)[:100]}...")
        
        # Check if state updated correctly
        time.sleep(0.5)

    print("\n=== SIMULATION: SUCCESS ===")
    print("Resulting audit_report.txt exists:", os.path.exists("audit_report.txt"))
    if os.path.exists("audit_report.txt"):
        with open("audit_report.txt", "r") as f:
            print("Report Content:", f.read())

if __name__ == "__main__":
    simulate()
