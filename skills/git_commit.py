"""
Skill: git_commit
Description: Automatically stages all changes and creates a git commit with a descriptive message. Useful for snapshotting known-good states.
"""

import sys
import subprocess
import os

def run(commit_message):
    try:
        # Check if it's a git repo
        if not os.path.exists(".git"):
            return "Error: This directory is not a Git repository. Cannot commit."
            
        # Stage all changes
        add_res = subprocess.run(["git", "add", "."], capture_output=True, text=True)
        if add_res.returncode != 0:
            return f"Error staging files: {add_res.stderr}"
            
        # Check if there's anything to commit
        status_res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not status_res.stdout.strip():
            return "No changes to commit (working tree clean)."
            
        # Commit
        commit_res = subprocess.run(["git", "commit", "-m", commit_message], capture_output=True, text=True)
        if commit_res.returncode == 0:
            return f"Success: Created commit '{commit_message}'\n{commit_res.stdout}"
        else:
            return f"Error creating commit: {commit_res.stderr}\n{commit_res.stdout}"
            
    except Exception as e:
        return f"Git commit failed unexpectedly: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: git_commit <commit_message>")
        sys.exit(1)
    
    # Re-join all args in case the model didn't quote the message properly
    msg = " ".join(sys.argv[1:])
    print(run(msg))
