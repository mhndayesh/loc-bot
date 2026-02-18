
"""
gen_pass: Generates a password.
"""
import subprocess
import sys

def run(length=12):
    return subprocess.check_output(["python", "gen_pass.py", str(length)], text=True).strip()

if __name__ == "__main__":
    print(run(sys.argv[1] if len(sys.argv)>1 else 12))
