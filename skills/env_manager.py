
"""env_manager: Manage Python virtual environments."""
import os
import sys
import json
import subprocess
import shutil
import platform

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_DIR = os.path.join(BASE_DIR, "environments")
ENV_MAP_FILE = os.path.join(BASE_DIR, "environments.json")
MAP_MD_FILE = os.path.join(BASE_DIR, "MAP.md")

def load_env_map():
    if os.path.exists(ENV_MAP_FILE):
        with open(ENV_MAP_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_env_map(data):
    with open(ENV_MAP_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    sync_to_map_md(data)

def sync_to_map_md(data):
    """Update MAP.md with current environments."""
    if not os.path.exists(MAP_MD_FILE):
        return

    with open(MAP_MD_FILE, 'r') as f:
        content = f.read()

    start_marker = "## Environments"
    if start_marker not in content:
        # Append if missing
        content += f"\n\n{start_marker}\nManaged virtual environments and tool mappings:\n*(No environments created yet)*"
    
    # Split content
    parts = content.split(start_marker)
    pre_content = parts[0]
    
    # Generate new section
    new_section = f"{start_marker}\nManaged virtual environments and tool mappings:\n"
    if not data:
        new_section += "*(No environments created yet)*"
    else:
        for name, details in data.items():
            new_section += f"- **{name}** ({details['type']}): `{details['path']}`\n"
            if details.get("packages"):
                new_section += f"  - Packages: {', '.join(details['packages'])}\n"

    # Reconstruct. Note: We discard whatever was after the marker originally if it was just the list.
    # If there were other sections after, this is risky. Ideally we regex replace the section.
    # For now, assuming Environments is at the end or strictly governed.
    # Let's try to be safer: Find next ## if exists.
    
    post_content = ""
    # Check if parts[1] has another section
    if len(parts) > 1 and "## " in parts[1]:
        # There is another section
        subparts = parts[1].split("\n## ", 1)
        if len(subparts) > 1:
            post_content = "\n## " + subparts[1]
    
    with open(MAP_MD_FILE, 'w') as f:
        f.write(pre_content + new_section + post_content)

def run(action, name=None, packages=None, env_type="python"):
    """
    Manage environments.
    actions: create, install, list, delete
    name: name of environment
    packages: list of packages (space separated string or list)
    env_type: "python" or "node"
    """
    data = load_env_map()

    if action == "list":
        return json.dumps(data, indent=2)

    if action == "create":
        if not name: return "Error: Name required for create."
        
        path = os.path.join(ENV_DIR, name)
        if name in data: return f"Error: Environment {name} already exists."
        
        try:
            if env_type == "python":
                subprocess.check_call([sys.executable, "-m", "venv", path])
                
                # Upgrade pip safely
                if platform.system() == "Windows":
                    python_exe = os.path.join(path, "Scripts", "python")
                else:
                    python_exe = os.path.join(path, "bin", "python")
                
                try:
                    subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
                except subprocess.CalledProcessError:
                    print(f"Warning: Failed to upgrade pip in {name}, continuing...")
                
            elif env_type == "node":
                os.makedirs(path, exist_ok=True)
                npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
                subprocess.check_call([npm_cmd, "init", "-y"], cwd=path)
            
            data[name] = {"type": env_type, "path": path, "packages": []}
            save_env_map(data)
            return f"Environment {name} created at {path}"
        except Exception as e:
            return f"Error creating environment: {e}"

    if action == "install":
        if not name or name not in data: return f"Error: Environment {name} not found."
        if not packages: return "Error: Packages required."
        
        path = data[name]["path"]
        env_type = data[name]["type"]
        pkgs = packages.split() if isinstance(packages, str) else packages
        
        try:
            if env_type == "python":
                if platform.system() == "Windows":
                    python_exe = os.path.join(path, "Scripts", "python")
                else:
                    python_exe = os.path.join(path, "bin", "python")
                cmd = [python_exe, "-m", "pip", "install"] + pkgs
                subprocess.check_call(cmd)
                
            elif env_type == "node":
                npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
                cmd = [npm_cmd, "install"] + pkgs
                subprocess.check_call(cmd, cwd=path)
            
            # Update record
            existing = set(data[name].get("packages", []))
            existing.update(pkgs)
            data[name]["packages"] = list(existing)
            save_env_map(data)
            return f"Installed {packages} in {name}"
        except Exception as e:
            return f"Error installing packages: {e}"

    if action == "delete":
        if not name or name not in data: return f"Error: Environment {name} not found."
        path = data[name]["path"]
        try:
            shutil.rmtree(path)
            del data[name]
            save_env_map(data)
            return f"Environment {name} deleted."
        except Exception as e:
            return f"Error deleting environment: {e}"

    return "Error: Unknown action"

if __name__ == "__main__":
    # Test
    pass
