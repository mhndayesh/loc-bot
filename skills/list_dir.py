"""
List the contents of a specified directory.
Usage: LIST_DIR(path)
"""
import os
import argparse
import sys

def run():
    parser = argparse.ArgumentParser(description="List directory contents")
    parser.add_argument("path", nargs="?", default="workspace", help="Path to list (default: workspace)")
    parser.add_argument("--all", action="store_true", help="Include hidden files")
    args = parser.parse_args()

    target_path = os.path.abspath(args.path)
    
    if not os.path.exists(target_path):
        print(f"Error: Path does not exist: {target_path}")
        sys.exit(1)
        
    if not os.path.isdir(target_path):
        print(f"Error: Path is not a directory: {target_path}")
        sys.exit(1)

    try:
        entries = os.listdir(target_path)
        if not args.all:
            entries = [e for e in entries if not e.startswith('.')]
            
        entries.sort()
        
        print(f"Contents of {target_path}:")
        for entry in entries:
            full_path = os.path.join(target_path, entry)
            if os.path.isdir(full_path):
                print(f"[DIR]  {entry}")
            else:
                size_kb = os.path.getsize(full_path) / 1024
                print(f"[FILE] {entry} ({size_kb:.1f} KB)")
                
    except Exception as e:
        print(f"Error listing directory: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
