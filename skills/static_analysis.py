"""
Skill: static_analysis
Description: Runs flake8 on a Python file to detect syntax errors and obvious bugs before execution.
"""

import sys
import subprocess
import os

def run(filepath):
    try:
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' does not exist."
            
        if not filepath.endswith(".py"):
            return f"Error: '{filepath}' is not a Python file."

        # Check if flake8 is installed
        check_res = subprocess.run([sys.executable, "-m", "flake8", "--version"], capture_output=True, text=True)
        if check_res.returncode != 0:
            return "Error: flake8 is not installed. Please run `pip install flake8`."
            
        # Run flake8 with relaxed rules (ignore formatting, focus on bugs)
        # E9, F63, F7, F82 are syntax/logic errors. F401 is unused import. F841 is unused variable. E501 is line length (ignored).
        cmd = [sys.executable, "-m", "flake8", "--select=E9,F63,F7,F82,F401,F841", filepath]
        res = subprocess.run(cmd, capture_output=True, text=True)
        
        if res.returncode == 0:
            return f"Success: No major syntax errors or undefined names found in '{filepath}'."
        else:
            return f"Issues found in '{filepath}':\n{res.stdout}\n{res.stderr}"
            
    except Exception as e:
        return f"Static analysis failed: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: static_analysis <python_file.py>")
        sys.exit(1)
        
    print(run(sys.argv[1]))
