
"""
seed_instructions.py
Extracts hardcoded rules and seeds them into the Vector DB.
"""
import sys
import os
import time
import glob
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import memory

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge")

# 1. CORE RULES
core_rules = [
    "1. **THINK THEN ACT**: Every response must have `[THINK]...[/THINK]` BEFORE `[TOOL]...[/TOOL]`.",
    "2. **ONE ACTION PER TURN**: Do exactly one thing, then wait for the result.",
    "3. **SAVE STATE**: After every meaningful action, call `update_state`.",
    "4. **SELF-FIX**: If a tool fails, read `JOURNAL.md`, reason about why, then try differently.",
    "Reason in `[THINK]...[/THINK]` tags before acting.",
    "Tools MUST use `[TOOL] name(args) [/TOOL]` syntax."
]

# 2. RESPONSE FORMAT
response_format = """
You MUST always respond in this exact format:
```
[THINK]
I need to ___. My goal is ___. 
Looking at my recent journal, I see ___.
The best next step is ___ because ___.
[/THINK]

[TOOL] tool_name("argument1", "argument2") [/TOOL]
```
"""

# 3. TOOL DEFINITIONS (Simplified for retrieval)
tools = [
    "To read a file, use: `read_file(\"path/to/file\")`",
    "To write a file, use: `write_file(\"path/to/file\", \"content\")`",
    "To append to a file, use: `append_file(\"path/to/file\", \"content\")`",
    "To list a directory, use: `list_dir(\"path\")`",
    "To run a shell command, use: `run_command(\"command\")`",
    "To create a new tool, use: `create_tool(\"name\", \"python_code\")`",
    "To update your goal/status, use: `update_state(\"goal\", \"status\")`",
    "To recall memories, use: `recall(\"query\")`",
    "To save a memory, use: `memorize(\"content\")`"
]

# 4. THINKING GUIDELINES
thinking = """
When you think, answer these questions:
1. **Where am I?** What is my current goal and status?
2. **What just happened?** Look at RECENT JOURNAL and RECENT THOUGHTS.
3. **What should I do next?** Pick the single best action.
4. **Why this action?** Justify your choice in one sentence.
"""

# 5. ERROR HANDLING
errors = """
If a tool returns an error:
1. Stop and THINK about what went wrong.
2. Read `JOURNAL.md` to see the last few actions and results.
3. In your `[THINK]` block, say: "I failed because ___. I will now try ___."
"""

def seed():
    print("Beginning Knowledge Migration...")
    
    # Batch 1: Core Rules
    print("Seeding Core Rules...")
    for rule in core_rules:
        memory.learn_instruction(f"CORE RULE: {rule}")
        
    # Batch 2: formatting
    print("Seeding Formats...")
    memory.learn_instruction(f"RESPONSE FORMAT:\n{response_format}")
    
    # Batch 3: Tools
    print("Seeding Tools...")
    for t in tools:
        memory.learn_instruction(f"TOOL USAGE: {t}")
        
    # Batch 4: Thinking
    print("Seeding Thinking Guidelines...")
    memory.learn_instruction(f"THINKING STRATEGY:\n{thinking}")
    
    # Batch 5: Errors
    print("Seeding Error Protocols...")
    memory.learn_instruction(f"ERROR PROTOCOL:\n{errors}")

    # Batch 6: Knowledge Files
    print("Seeding Detailed Knowledge...")
    ingest_knowledge(KNOWLEDGE_DIR)
    
    # Batch 7: Workspace Docs
    print("Seeding Workspace Documentation...")
    workspace_docs = [
        "README.md", "RULES.md", "SKILLS.md", "SOUL.md", "SUMMARY.md", "AGENT_MANUAL.md"
    ]
    for doc in workspace_docs:
        doc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), doc)
        if os.path.exists(doc_path):
            print(f"  > Processing {doc}...")
            ingest_file(doc_path)
            
    # Batch 8: Docs Folder
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
    if os.path.exists(docs_dir):
        print("Seeding 'docs/' folder...")
        files = glob.glob(os.path.join(docs_dir, "*.md"))
        for fpath in files:
            print(f"  > Processing docs/{os.path.basename(fpath)}...")
            ingest_file(fpath)

    print("Migration Complete.")

def ingest_file(fpath):
    fname = os.path.basename(fpath)
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Robust split by H2 headers (## )
        sections = re.split(r'(?m)^## ', content)
        
        # First chunk
        title_chunk = sections[0].strip()
        if title_chunk:
            memory.learn_instruction(f"DOC ({fname}):\n{title_chunk}")
            
        # Rest
        for section in sections[1:]:
            full_section = "## " + section.strip()
            memory.learn_instruction(f"DOC ({fname}):\n{full_section}")
    except Exception as e:
        print(f"    Error reading {fname}: {e}")

def ingest_knowledge(target_dir):
    if not os.path.exists(target_dir):
        print(f"Skipping ingest: {target_dir} not found.")
        return

    files = glob.glob(os.path.join(target_dir, "*.md"))
    for fpath in files:
        print(f"  > Processing knowledge/{os.path.basename(fpath)}...")
        ingest_file(fpath)

if __name__ == "__main__":
    # Force local embedding for speed/reliability during seed
    memory.maker.provider = "local"
    seed()
