
"""verify_context: Double-check project files and environment status."""
import os
import sys
import platform
import subprocess

def run_verify():
    print("=== ENVIRONMENT DIAGNOSTICS ===")
    
    # 1. Identity
    try:
        user = os.getlogin()
        print(f"User: {user}")
    except:
        print("User: (unknown)")
        
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    
    # 2. Location
    cwd = os.getcwd()
    print(f"CWD: {cwd}")
    
    # 3. Permissions test
    try:
        test_file = os.path.join(cwd, ".perm_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        print("Write Permission: OK")
    except Exception as e:
        print(f"Write Permission: FAIL ({e})")
        
    # 4. Recent Files (what's happening around me?)
    print("\n--- Recent Interactions (Modified < 10min) ---")
    try:
        import time
        now = time.time()
        count = 0
        for root, dirs, files in os.walk(cwd):
            if ".git" in root or "__pycache__" in root:
                continue
            for f in files:
                path = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(path)
                    if now - mtime < 600: # 10 mins
                        print(f"- {f} ({int(now - mtime)}s ago)")
                        count += 1
                except:
                    pass
            if count > 10:
                print("... (and more)")
                break
    except Exception as e:
        print(f"Error scanning files: {e}")

    print("===============================")

if __name__ == "__main__":
    run_verify()
