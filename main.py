import sys
import os

# Ensure the project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.paths import ensure_dirs, PROJECT_ROOT
from src.api.server import ThreadingHTTPServer, AgentAPIHandler, load_config
import logging

def main():
    # Ensure all professional structure directories exist
    ensure_dirs()
    
    # Load configuration to get the port
    config = load_config()
    port = config.get("port", 7777)
    
    # Initialize the server
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, AgentAPIHandler)
    
    print("\n" + "="*30)
    print("      MO THE BOT - ACTIVE")
    print("="*30)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"API Server:   http://localhost:{port}")
    print(f"GUI:          Serving from frontend/")
    print("="*30 + "\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    main()
