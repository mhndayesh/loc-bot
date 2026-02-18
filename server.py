"""
new-agent-mohannad: Web Server
Provides a REST API and serves the GUI for controlling the agent.
"""
import os
import json
import threading
import time
import http.client
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging
import collections
import memory
from engine import AgentEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GUI_DIR = os.path.join(BASE_DIR, "gui")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
JOURNAL_FILE = os.path.join(BASE_DIR, "JOURNAL.md")
SCRATCHPAD_FILE = os.path.join(BASE_DIR, "SCRATCHPAD.md")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger("server")

# ── Heartbeat thread control ──────────────────────────────────────────
heartbeat_thread = None
heartbeat_running = False
LOG_BUFFER = collections.deque(maxlen=2000)

# Attach buffer handler to root logger
# REMOVED BufferHandler to avoid duplication with ConsoleInterceptor

import sys
class ConsoleInterceptor:
    def __init__(self, original_stream):
        self.original_stream = original_stream
    def write(self, data):
        if data.strip():
            # Avoid infinite loop if logger writes to stdout
            # log.info calls use the StreamHandler which writes to sys.stderr (usually)
            # but we want to capture everything else
            LOG_BUFFER.append(data.strip())
        self.original_stream.write(data)
    def flush(self):
        self.original_stream.flush()

sys.stdout = ConsoleInterceptor(sys.stdout)
sys.stderr = ConsoleInterceptor(sys.stderr)
print("Agent terminal system active via port 7777.")
print("Waiting for pulses or user activity...")


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default or {}

import time
import uuid

def save_json(path, data):
    tmp = path + f".tmp_{uuid.uuid4().hex}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        # Retry loop for Windows file locking
        retries = 3
        for i in range(retries):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if i == retries - 1:
                    raise
                time.sleep(0.1)
    except Exception as e:
        log.error("Atomic save failed for %s: %s", path, e)
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except:
                pass


def read_file_safe(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return default


def cleanup_old_logs():
    """Rotate logs: keep only the last 50 pulse files in memory/."""
    try:
        if not os.path.exists(MEMORY_DIR):
            return
        files = [os.path.join(MEMORY_DIR, f) for f in os.listdir(MEMORY_DIR) if f.startswith("pulse_")]
        if len(files) > 500:
            # Sort by modification time (oldest first)
            files.sort(key=os.path.getmtime)
            to_delete = files[:-500]
            count = 0
            for f in to_delete:
                try:
                    os.remove(f)
                    count += 1
                except Exception:
                    pass
            log.info("Cleaned up %d old pulse logs.", count)
    except Exception as e:
        log.warning("Log cleanup failed: %s", e)


def load_config(path=CONFIG_FILE):
    """Load config with validation and default fallback."""
    defaults = {
        "provider": "ollama",
        "providers": {
            "ollama": {"base_url": "http://localhost:11434", "api_key": "ollama", "default_model": "llama3.2:3b"}
        },
        "permissions": {
            "run_command": True, "write_file": True, "read_file": True, "list_dir": True
        }
    }
    
    cfg = load_json(path, {})
    
    # 1. Validate JSON structure (must be dict)
    if not isinstance(cfg, dict):
        log.error("Config is not a dictionary. Using defaults.")
        return defaults
    
    # 2. Check essential keys
    if "providers" not in cfg:
        cfg["providers"] = defaults["providers"]
    
    # Ensure permissions dict exists
    if "permissions" not in cfg:
        cfg["permissions"] = defaults["permissions"]
        
    return cfg


def run_heartbeat():
    """Run the engine in a heartbeat loop in a background thread."""
    global heartbeat_running
    import subprocess, sys
    engine_path = os.path.join(BASE_DIR, "engine.py")

    while heartbeat_running:
        # Re-read config & status every pulse
        config = load_config()
        state = load_json(STATE_FILE, {"status": "ready"})
        
        # Determine interval: fast if working/recovering, slow otherwise
        base_interval = config.get("heartbeat_interval", 60)
        if base_interval <= 0:
            base_interval = 60 # Prevent busy loop if set to 0 (disabled)
            
        status = state.get("status", "ready")
        
        if status in ("working", "recovering"):
            interval = 0.5  # Fast loop for active work
        elif state.get("goal") and state.get("goal").lower().strip() != "done":
            interval = 1.0  # Autonomous goal pursuit mode
        else:
            interval = base_interval

        try:
            env = os.environ.copy()
            provider_key = config.get("provider", "ollama")
            provider = config.get("providers", {}).get(provider_key, {})
            env["AGENT_API_URL"] = provider.get("base_url", "http://localhost:11434")
            env["AGENT_API_KEY"] = provider.get("api_key", "ollama")
            env["AGENT_API_FORMAT"] = provider.get("api_format", "ollama")
            env["AGENT_MODEL"] = config.get("model", "llama3.2:3b")

            # --- Reflection Trigger (Dreaming) ---
            current_time = time.time()
            last_activity = state.get("last_reply_ts", 0)
            last_reflection = state.get("last_reflection_ts", 0)
            REFLECT_THRESHOLD = 1800 # 30 minutes
            
            if (current_time - last_activity > REFLECT_THRESHOLD) and (last_activity > last_reflection):
                log.info("Agent idle for %d seconds. Triggering Memory Reflection...", int(current_time - last_activity))
                subprocess.run(
                    [sys.executable, engine_path, "--once", "--mode", "reflect"],
                    env=env, capture_output=True
                )
            
            # --- Active Goal Pursuit Trigger ---
            goal = state.get("goal", "").lower().strip()
            is_active = (goal != "" and goal != "done")
            mode = "chat" if is_active else "heartbeat"
            
            with subprocess.Popen(
                [sys.executable, engine_path, "--once", "--mode", mode],
                env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, encoding='utf-8', errors='replace'
            ) as proc:
                if proc.stdout:
                    for line in proc.stdout:
                        LOG_BUFFER.append(line.rstrip())
            
        except Exception as e:
            log.error("Pulse error: %s", e)
        
        # Responsive Sleep: Sleep in 1s increments to check for goal changes
        slept = 0
        while slept < interval and heartbeat_running:
            time.sleep(1)
            slept += 1
            # Check if state changed during sleep
            try:
                with open(STATE_FILE, "r") as f:
                    new_state = json.load(f)
                if new_state.get("goal") != state.get("goal") or new_state.get("status") != state.get("status"):
                    break # Wake up early (state changed)
                
                # Also check for interval changes (e.g. user reduced it)
                new_config = load_config()
                if new_config.get("heartbeat_interval", 60) < interval:
                    log.info("Heartbeat interval reduced. Waking up early.")
                    break
            except:
                pass


class AgentAPIHandler(SimpleHTTPRequestHandler):
    """Serve GUI static files + REST API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=GUI_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        # ── API endpoints ──────────────────────────────────────────────
        if path == "/api/status":
            state = load_json(STATE_FILE, {"goal": "", "status": "ready", "progress": []})
            config = load_config()
            journal = read_file_safe(JOURNAL_FILE)
            scratchpad = read_file_safe(SCRATCHPAD_FILE)

            # Count pulse files
            pulse_count = 0
            try:
                pulse_count = len([f for f in os.listdir(MEMORY_DIR) if f.startswith("pulse_")])
            except Exception:
                pass

            self._json_response({
                "state": state,
                "config": config,
                "journal": journal[-2000:],
                "scratchpad": scratchpad[-1500:],
                "heartbeat_running": heartbeat_running,
                "pulse_count": pulse_count,
            })
            return

        if path == "/api/config":
            self._json_response(load_json(CONFIG_FILE))
            return

        if path == "/api/providers":
            config = load_config()
            providers = config.get("providers", {})
            active = config.get("provider", "ollama")
            self._json_response({"providers": providers, "active": active})
            return

        if path == "/api/models":
            config = load_config()
            provider_key = config.get("provider", "ollama")
            provider = config.get("providers", {}).get(provider_key, {})
            base_url = provider.get("base_url", "http://localhost:11434")
            api_format = provider.get("api_format", "ollama")
            api_key = provider.get("api_key", "")
            models = []
            try:
                parsed = urlparse(base_url)
                if parsed.scheme == "https":
                    conn = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=5)
                else:
                    conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 11434, timeout=5)
                if api_format == "ollama":
                    conn.request("GET", "/api/tags")
                    resp = conn.getresponse()
                    data = json.loads(resp.read().decode())
                    models = [m["name"] for m in data.get("models", [])]
                else:
                    headers = {"Authorization": f"Bearer {api_key}"}
                    conn.request("GET", "/v1/models", headers=headers)
                    resp = conn.getresponse()
                    data = json.loads(resp.read().decode())
                    models = [m["id"] for m in data.get("data", [])]
                conn.close()
            except Exception as e:
                log.error("Failed to fetch models: %s", e)
            self._json_response({"models": models, "provider": provider_key})
            return

        if path == "/api/embedding_models":
            config = load_config()
            provider_key = config.get("embedding_provider", "local")
            if provider_key == "local":
                # Local models are usually managed by the library, but we can return some defaults
                self._json_response({"models": ["all-MiniLM-L6-v2", "multi-qa-MiniLM-L6-dot-v1"], "provider": "local"})
                return
            
            provider = config.get("providers", {}).get(provider_key, {})
            base_url = provider.get("base_url", "http://localhost:11434")
            api_format = provider.get("api_format", "ollama")
            api_key = provider.get("api_key", "")
            models = []
            try:
                parsed = urlparse(base_url)
                if parsed.scheme == "https":
                    conn = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=5)
                else:
                    conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 11434, timeout=5)
                if api_format == "ollama":
                    conn.request("GET", "/api/tags")
                    resp = conn.getresponse()
                    data = json.loads(resp.read().decode())
                    models = [m["name"] for m in data.get("models", [])]
                else:
                    headers = {"Authorization": f"Bearer {api_key}"}
                    conn.request("GET", "/v1/models", headers=headers)
                    resp = conn.getresponse()
                    data = json.loads(resp.read().decode())
                    models = [m["id"] for m in data.get("data", [])]
                conn.close()
            except Exception as e:
                log.error("Failed to fetch embedding models: %s", e)
            self._json_response({"models": models, "provider": provider_key})
            return

        if path == "/api/logs":
            self._json_response({"logs": list(LOG_BUFFER)})
            return

        # ── Static file fallback ───────────────────────────────────────
        if path == "/" or path == "":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        global heartbeat_thread, heartbeat_running
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        if path == "/api/stop":
            state = load_json(STATE_FILE, {})
            state["goal"] = "done"
            state["status"] = "stopped"
            save_json(STATE_FILE, state)
            log.info("SYSTEM STOP requested via API.")
            self._json_response({"ok": True, "message": "Agent stopped."})
            return

        if path == "/api/config":
            config = load_config()
            config.update(body)
            save_json(CONFIG_FILE, config)
            self._json_response({"ok": True})
            return

        if path == "/api/provider":
            config = load_config()
            new_provider = body.get("provider")
            if new_provider and (new_provider in config.get("providers", {}) or new_provider == "local"):
                config["provider"] = new_provider
                # Update model to provider default
                if new_provider in config.get("providers", {}):
                    config["model"] = config["providers"][new_provider].get("default_model", config.get("model"))
                save_json(CONFIG_FILE, config)
                self._json_response({"ok": True, "provider": new_provider})
            else:
                self._json_response({"error": "Unknown provider"}, 400)
            return

        if path == "/api/embedding_provider":
            config = load_config()
            new_provider = body.get("provider")
            # Allow "local" or any known providers
            if new_provider and (new_provider in config.get("providers", {}) or new_provider == "local"):
                config["embedding_provider"] = new_provider
                save_json(CONFIG_FILE, config)
                self._json_response({"ok": True, "provider": new_provider})
            else:
                self._json_response({"error": "Unknown embedding provider"}, 400)
            return

        if path == "/api/goal":
            state = load_json(STATE_FILE)
            state["goal"] = body.get("goal", "")
            state["status"] = "ready"
            state["last_error"] = None
            save_json(STATE_FILE, state)
            self._json_response({"ok": True})
            return

        if path == "/api/heartbeat/start":
            if not heartbeat_running:
                heartbeat_running = True
                heartbeat_thread = threading.Thread(target=run_heartbeat, daemon=True)
                heartbeat_thread.start()
                log.info("Heartbeat started via GUI.")
            self._json_response({"running": True})
            return

        if path == "/api/heartbeat/stop":
            heartbeat_running = False
            log.info("Heartbeat stopped via GUI.")
            self._json_response({"running": False})
            return

        if path == "/api/pulse":
            # Run a single pulse immediately
            import subprocess, sys
            engine_path = os.path.join(BASE_DIR, "engine.py")
            config = load_config()
            env = os.environ.copy()
            provider_key = config.get("provider", "ollama")
            provider = config.get("providers", {}).get(provider_key, {})
            env["AGENT_API_URL"] = provider.get("base_url", "http://localhost:11434")
            env["AGENT_API_KEY"] = provider.get("api_key", "ollama")
            env["AGENT_API_FORMAT"] = provider.get("api_format", "ollama")
            env["AGENT_MODEL"] = config.get("model", "llama3.2:3b")
            
            pulse_mode = body.get("type", "chat")
            cmd = [sys.executable, engine_path, "--once", "--mode", pulse_mode]

            try:
                result = subprocess.run(
                    cmd,
                    timeout=120, env=env, capture_output=True, text=True,
                )
                self._json_response({"ok": True, "output": result.stdout[-500:]})
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
            return

        if path == "/api/permissions":
            config = load_config()
            config["permissions"] = body.get("permissions", config.get("permissions", {}))
            save_json(CONFIG_FILE, config)
            self._json_response({"ok": True})
            return

        if path == "/api/clear/journal":
            with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
                f.write("# JOURNAL.md\n\n")
            self._json_response({"ok": True})
            return

        if path == "/api/clear/scratchpad":
            with open(SCRATCHPAD_FILE, "w", encoding="utf-8") as f:
                f.write("# SCRATCHPAD.md\n\n")
            self._json_response({"ok": True})
            return

        # ── Session Management ──────────────────────────────────────────
        if path == "/api/chat/sessions":
            sessions_dir = os.path.join(MEMORY_DIR, "chat_sessions")
            os.makedirs(sessions_dir, exist_ok=True)
            sessions = []
            for fname in sorted(os.listdir(sessions_dir), reverse=True):
                if fname.endswith(".json"):
                    s = load_json(os.path.join(sessions_dir, fname))
                    sessions.append({
                        "id": s.get("id", fname.replace(".json", "")),
                        "title": s.get("title", "Untitled"),
                        "created": s.get("created", ""),
                        "message_count": len(s.get("messages", [])),
                    })
            self._json_response({"sessions": sessions})
            return

        if path == "/api/chat/save":
            sessions_dir = os.path.join(MEMORY_DIR, "chat_sessions")
            os.makedirs(sessions_dir, exist_ok=True)
            sid = body.get("id") or f"chat_{int(time.time())}"
            messages = body.get("messages", [])
            title = body.get("title", "")

            # Auto-generate title from first user message if not provided
            if not title and messages:
                for m in messages:
                    if m.get("role") == "user":
                        title = m.get("content", "")[:60]
                        if len(m.get("content", "")) > 60:
                            title += "..."
                        break
            if not title:
                title = "Untitled Chat"

            session_data = {
                "id": sid,
                "title": title,
                "created": body.get("created") or time.strftime("%Y-%m-%d %H:%M"),
                "messages": messages,
            }
            save_json(os.path.join(sessions_dir, f"{sid}.json"), session_data)
            self._json_response({"ok": True, "id": sid, "title": title})
            return

        if path == "/api/chat/load":
            sessions_dir = os.path.join(MEMORY_DIR, "chat_sessions")
            sid = body.get("id", "")
            fpath = os.path.join(sessions_dir, f"{sid}.json")
            if os.path.exists(fpath):
                session_data = load_json(fpath)
                self._json_response(session_data)
            else:
                self._json_response({"error": "Session not found"}, 404)
            return

        if path == "/api/chat/delete":
            sessions_dir = os.path.join(MEMORY_DIR, "chat_sessions")
            sid = body.get("id", "")
            fpath = os.path.join(sessions_dir, f"{sid}.json")
            if os.path.exists(fpath):
                os.remove(fpath)
                self._json_response({"ok": True})
            else:
                self._json_response({"error": "Session not found"}, 404)
            return

        # ── Chat ───────────────────────────────────────────────────────
        if path == "/api/chat":
            user_msg = body.get("message", "")
            files = body.get("files", [])  # [{name, type, content}]
            history = body.get("history", [])  # previous messages

            # Build content with file attachments
            content_parts = []
            image_payloads = [] # List of {mime, b64}
            if user_msg:
                content_parts.append(user_msg)
            for f in files:
                fname = f.get("name", "file")
                ftype = f.get("type", "image/jpeg")
                fcontent = f.get("content", "") # This is data:image/...;base64,...
                if ftype.startswith("image/"):
                    if "," in fcontent:
                        b64 = fcontent.split(",", 1)[1]
                        image_payloads.append({"mime": ftype, "b64": b64})
                    content_parts.append(f"\n[Attached image: {fname}]")
                elif ftype.startswith("video/") or ftype.startswith("audio/"):
                    content_parts.append(f"\n[Attached {ftype.split('/')[0]}: {fname}]")
                else:
                    content_parts.append(f"\n--- File: {fname} ---\n{fcontent}\n--- End of {fname} ---")

            if image_payloads:
                log.info("Detected %d image(s) for LLM payload.", len(image_payloads))

            full_text = "\n".join(content_parts) if content_parts else "(empty)"
            
            # Formulate user message
            user_msg_obj = {"role": "user", "content": full_text}
            if image_payloads:
                # Store payloads in the message for later transformation
                user_msg_obj["_image_payloads"] = image_payloads
                user_msg_obj["images"] = [x["b64"] for x in image_payloads] # For Ollama compatibility

            # Build agent-aware system prompt
            config = load_json(CONFIG_FILE)
            provider_key = config.get("provider", "ollama")
            provider = config.get("providers", {}).get(provider_key, {})
            base_url = provider.get("base_url", "http://localhost:11434")
            api_key = provider.get("api_key", "ollama")
            model = config.get("model", provider.get("default_model", "llama3.2:3b"))
            fmt = provider.get("api_format", "ollama")
            temp = config.get("temperature", 0.1)
            max_tokens = config.get("max_tokens", 0)
            thinking = config.get("thinking_enabled", True)

            sys_prompt = _build_chat_system_prompt(thinking)
            
            # --- JIT MEMORY RECALL (Core Intelligence) ---
            # Search for semantically similar past experiences for the GUI chat
            past_wisdom = memory.recall(user_msg)
            if past_wisdom:
                log.info("💡 [Memory/Chat] Injecting past wisdom into GUI context.")
                sys_prompt += f"\n\n## Past Experience (Wisdom)\nYou have solved a similar problem before. Use this to avoid repeating mistakes:\n---\n{past_wisdom}\n---\n"
            # ---------------------------------------------

            # Summarize old context if history is long
            # Use new trim_history logic for robust context management
            msgs_to_send = trim_history(history, max_chars=20000) # Leave room for system prompt & new msg
            
            messages = [{"role": "system", "content": sys_prompt}]
            for h in msgs_to_send:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            messages.append(user_msg_obj)

            # NORMALIZE FOR STRICT MODELS (Gemma 3, etc.)
            messages = normalize_messages(messages)

            # Call LLM
            try:
                p = urlparse(base_url)
                if p.scheme == "https":
                    conn = http.client.HTTPSConnection(p.hostname, p.port or 443, timeout=120)
                else:
                    conn = http.client.HTTPConnection(p.hostname, p.port or 11434, timeout=120)

                if fmt == "ollama":
                    endpoint = "/api/chat"
                    payload = {"model": model, "messages": messages, "stream": False,
                               "options": {
                                   "temperature": temp, 
                                   "num_ctx": config.get("num_ctx", 2048),
                                   "num_predict": max_tokens if max_tokens > 0 else -1
                               }}
                    extract_fn = lambda d: d["message"]["content"]
                else:
                    # Transform for OpenAI Vision format if images are present
                    final_messages = []
                    for m in messages:
                        payloads = m.get("_image_payloads", [])
                        if m.get("role") == "user" and payloads:
                            content_list = [{"type": "text", "text": m["content"]}]
                            for p in payloads:
                                content_list.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{p['mime']};base64,{p['b64']}"}
                                })
                            final_messages.append({"role": "user", "content": content_list})
                        else:
                            # Strip helper keys
                            new_m = {k: v for k, v in m.items() if k not in ["images", "_image_payloads"]}
                            final_messages.append(new_m)
                            
                    endpoint = "/v1/chat/completions"
                    payload = {"model": model, "messages": final_messages, "temperature": temp}
                    if max_tokens > 0:
                        payload["max_tokens"] = max_tokens
                    extract_fn = lambda d: d["choices"][0]["message"]["content"]
                    
                    # DEBUG LOG (Truncated)
                    log.debug("Sending OpenAI payload with %d messages. Images: %s", 
                              len(final_messages), "Yes" if any("_image_payloads" in m or isinstance(m.get("content"), list) for m in messages) else "No")

                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
                conn.request("POST", endpoint, json.dumps(payload), headers)
                resp = conn.getresponse()
                resp_body = resp.read().decode()
                conn.close()

                if resp.status != 200:
                    self._json_response({"error": f"LLM returned HTTP {resp.status}: {resp_body[:300]}"}, 502)
                    return

                data = json.loads(resp_body)
                reply = extract_fn(data)

                # --- TOOL EXECUTION INTEGRATION ---
                # Instantiate a transient engine to process chat-based tool calls
                engine = AgentEngine()
                
                # 1. Save thinking to scratchpad (if any)
                thinking = engine.parse_thinking(reply)
                if thinking:
                    engine.save_thinking(thinking)
                
                # 2. Execute tools (if any)
                tool_result = engine.parse_and_run(reply)
                if tool_result:
                    log.info("Chat Tool Executed: %s", tool_result)
                    # We could append the result to the reply, but often the 
                    # agent's natural text already explains what it's doing.
                    # For now, we'll just allow the side-effects to happen.
                # ----------------------------------

                self._json_response({"reply": reply})
            except Exception as e:
                self._json_response({"error": f"LLM call failed: {e}"}, 502)
            return

        self._json_response({"error": "Not found"}, 404)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode())
        except Exception:
            return {}

    def _json_response(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        if "/api/" in str(args[0]):
            log.debug(format, *args)


# ── Agent-aware system prompt builder ─────────────────────────────────
def trim_history(history, max_chars=24000):
    """
    Trim message history to fit within a character-based context budget.
    Prioritizes keeping recent messages and strips base64 from older turns.
    """
    if not history:
        return []
        
    trimmed = []
    current_chars = 0
    
    # Process history backwards (most recent first)
    # We keep images only for the very last turn in history if it exists
    for i, m in enumerate(reversed(history)):
        msg_copy = dict(m)
        content = str(msg_copy.get("content", ""))
        
        # Strip heavy base64 images from older messages (i > 0 because it's reversed)
        if i > 0 and msg_copy.get("images"):
            # Keep a note that images were here but stripped for context
            msg_copy["images"] = []
            if "_image_payloads" in msg_copy: 
                msg_copy["_image_payloads"] = []
            content += "\n(Note: Image data removed from history to save context space)"
            msg_copy["content"] = content

        msg_len = len(content)
        if current_chars + msg_len > max_chars:
            # If we hit the limit, we stop adding older messages
            break
            
        trimmed.insert(0, msg_copy)
        current_chars += msg_len
        
    return trimmed


def normalize_messages(messages):
    """
    Ensure conversation roles alternate (system, user, assistant, user...).
    Merges consecutive same-role messages and handles non-user starts.
    """
    if not messages:
        return []
        
    result = []
    
    # 1. Maintain System if it's the first message
    temp_msgs = list(messages)
    if temp_msgs and temp_msgs[0].get("role") == "system":
        result.append(temp_msgs[0])
        temp_msgs = temp_msgs[1:]
        
    for m in temp_msgs:
        role = m.get("role", "user")
        content = m.get("content", "")
        images = m.get("images", []) # Ollama style
        
        # Handle content that might be a list (vision/multimodal)
        if isinstance(content, list):
            text_parts = [p.get("text", "") for p in content if p.get("type") == "text"]
            content_str = "\n".join(text_parts).strip()
        else:
            content_str = str(content).strip()
            
        if not content_str and not images:
            continue
            
        if not result:
            if role == "assistant":
                result.append({"role": "user", "content": "..."})
            result.append(m)
        else:
            last = result[-1]
            if last["role"] == role:
                # Merge consecutive same roles
                if isinstance(last.get("content"), str) and isinstance(m.get("content"), str):
                    last["content"] += "\n\n" + m.get("content", "")
                
                # Merge Ollama images
                if images:
                    if "images" not in last: last["images"] = []
                    last["images"].extend(images)
                
                # Merge OpenAI payloads (helper key)
                m_payloads = m.get("_image_payloads", [])
                if m_payloads:
                    if "_image_payloads" not in last: last["_image_payloads"] = []
                    last["_image_payloads"].extend(m_payloads)
            else:
                if last["role"] == "system" and role == "assistant":
                    result.append({"role": "user", "content": "..."})
                result.append(m)
                
    return result


def _build_chat_system_prompt(thinking_enabled):
    """Build an ultra-lean system prompt that refers to MAP.md."""
    parts = []

    # 1. Identity & Hub Reference
    parts.append(
        "# SYSTEM IDENTITY\n"
        "You are **mo the bot**, local owner of this computer.\n"
        "Your entire world and all instructions are defined in **MAP.md**. Read it immediately to orient yourself."
    )

    # 2. Workspace
    parts.append(f"## Environment\nOS: Windows\nWorkspace: {BASE_DIR}\nMap: [MAP.md](file:///c:/new-agent-mohannad/MAP.md)")

    # 3. Mandatory Syntax & Format
    parts.append(
        "## Rules of Engagement\n"
        "1. ALWAYS reason inside `[THINK]...[/THINK]` (Required).\n"
        "2. ALL actions MUST use `[TOOL] read_file(\"MAP.md\") [/TOOL]` syntax. Use real tool names.\\n"
        "3. **OUTPUT FOLDER**: ALWAYS save generated files (scripts, code, reports) to the `output/` directory (e.g., `write_file(\"output/game.py\", ...)`). Do NOT use the root directory.\\n"
        "4. Be brief. Max 1-2 sentences for final answers.\\n"
        "4. For help on identity/rules/skills, refer to **MAP.md**.\n\n"
        "## Available Tools\n"
        "- `read_file(path)`: Read a file.\n"
        "- `write_file(path, content)`: Write/create a file.\n"
        "- `run_command(cmd)`: Run a shell command.\n"
        "- `list_dir(path)`: List directory contents.\n"
        "- `update_state(goal, status)`: Set your current goal and status.\n"
        "- `memorize(text, solution, rating)`: Store a lesson in vector memory.\n"
        "- `recall(query, n=3)`: Retrieve relevant memories.\n"
        "- `search_web(query)`: Search the web.\n"
        "- `system_stats()`: Get CPU/Memory/Disk status.\n"
    )

    return "\n\n".join(parts)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="new-agent-mohannad GUI server")
    parser.add_argument("--port", type=int, default=7777, help="Port to serve on")
    args = parser.parse_args()

    # Initial cleanup
    cleanup_old_logs()
    
    # Start heartbeat if configured
    cfg = load_config()
    if cfg.get("heartbeat_interval", 0) > 0:
        heartbeat_running = True
        heartbeat_thread = threading.Thread(target=run_heartbeat, daemon=True)
        heartbeat_thread.start()
        log.info("Heartbeat started via config (interval=%ds)", cfg.get("heartbeat_interval"))

    os.makedirs(GUI_DIR, exist_ok=True)
    server = HTTPServer(("127.0.0.1", args.port), AgentAPIHandler)
    log.info("GUI server running at http://localhost:%d", args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Server stopped.")

