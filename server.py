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


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default or {}


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_file_safe(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return default


def run_heartbeat():
    """Run the engine in a heartbeat loop in a background thread."""
    global heartbeat_running
    import subprocess, sys
    engine_path = os.path.join(BASE_DIR, "engine.py")

    while heartbeat_running:
        # Re-read config & status every pulse
        config = load_json(CONFIG_FILE)
        state = load_json(STATE_FILE, {"status": "ready"})
        
        # Determine interval: fast if working/recovering, slow otherwise
        base_interval = config.get("heartbeat_interval", 60)
        status = state.get("status", "ready")
        
        if status in ("working", "recovering"):
            interval = 0.5  # Fast loop for active work
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

            subprocess.run(
                [sys.executable, engine_path, "--once"],
                timeout=120, env=env,
                capture_output=True,
            )
            # log.info("Pulse completed.") # Reduce log spam
        except Exception as e:
            log.error("Pulse error: %s", e)
        time.sleep(interval)


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
            config = load_json(CONFIG_FILE)
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
            config = load_json(CONFIG_FILE)
            providers = config.get("providers", {})
            active = config.get("provider", "ollama")
            self._json_response({"providers": providers, "active": active})
            return

        if path == "/api/models":
            config = load_json(CONFIG_FILE)
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

        # ── Static file fallback ───────────────────────────────────────
        if path == "/" or path == "":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        global heartbeat_thread, heartbeat_running
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        if path == "/api/config":
            config = load_json(CONFIG_FILE)
            config.update(body)
            save_json(CONFIG_FILE, config)
            self._json_response({"ok": True})
            return

        if path == "/api/provider":
            config = load_json(CONFIG_FILE)
            new_provider = body.get("provider")
            if new_provider and new_provider in config.get("providers", {}):
                config["provider"] = new_provider
                # Update model to provider default
                config["model"] = config["providers"][new_provider].get("default_model", config.get("model"))
                save_json(CONFIG_FILE, config)
                self._json_response({"ok": True, "provider": new_provider})
            else:
                self._json_response({"error": "Unknown provider"}, 400)
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
            config = load_json(CONFIG_FILE)
            env = os.environ.copy()
            provider_key = config.get("provider", "ollama")
            provider = config.get("providers", {}).get(provider_key, {})
            env["AGENT_API_URL"] = provider.get("base_url", "http://localhost:11434")
            env["AGENT_API_KEY"] = provider.get("api_key", "ollama")
            env["AGENT_API_FORMAT"] = provider.get("api_format", "ollama")
            env["AGENT_MODEL"] = config.get("model", "llama3.2:3b")
            try:
                result = subprocess.run(
                    [sys.executable, engine_path, "--once"],
                    timeout=120, env=env, capture_output=True, text=True,
                )
                self._json_response({"ok": True, "output": result.stdout[-500:]})
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
            return

        if path == "/api/permissions":
            config = load_json(CONFIG_FILE)
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
            if user_msg:
                content_parts.append(user_msg)
            for f in files:
                fname = f.get("name", "file")
                ftype = f.get("type", "")
                fcontent = f.get("content", "")
                if ftype.startswith("image/"):
                    content_parts.append(f"\n[Attached image: {fname}]")
                elif ftype.startswith("video/") or ftype.startswith("audio/"):
                    content_parts.append(f"\n[Attached {ftype.split('/')[0]}: {fname}]")
                else:
                    content_parts.append(f"\n--- File: {fname} ---\n{fcontent}\n--- End of {fname} ---")

            full_message = "\n".join(content_parts) if content_parts else "(empty)"

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

            # Summarize old context if history is long
            msgs_to_send = history[-20:]
            if len(history) > 20:
                summary_note = f"[Previous {len(history) - 20} messages summarized: The conversation covered topics from the earlier messages.]"
                msgs_to_send = [{"role": "system", "content": summary_note}] + msgs_to_send

            messages = [{"role": "system", "content": sys_prompt}]
            for h in msgs_to_send:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            messages.append({"role": "user", "content": full_message})

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
                               "options": {"temperature": temp, "num_ctx": config.get("num_ctx", 2048)}}
                    extract_fn = lambda d: d["message"]["content"]
                else:
                    endpoint = "/v1/chat/completions"
                    payload = {"model": model, "messages": messages, "temperature": temp}
                    if max_tokens > 0:
                        payload["max_tokens"] = max_tokens
                    extract_fn = lambda d: d["choices"][0]["message"]["content"]

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
def _build_chat_system_prompt(thinking_enabled):
    """Build a rich system prompt that gives the AI full awareness of its project."""
    parts = []

    # Current state (PRIORITY: TOP OF PROMPT)
    state = load_json(STATE_FILE, {})
    if state.get("goal"):
        parts.append(f"# CURRENT AGENT GOAL\n{state['goal']}")

    # Identity
    soul = read_file_safe(os.path.join(BASE_DIR, "SOUL.md"))
    if soul:
        parts.append(f"# YOUR IDENTITY\n{soul.strip()}")

    # Project map
    map_content = read_file_safe(os.path.join(BASE_DIR, "MAP.md"))
    if map_content:
        parts.append(f"# YOUR PROJECT STRUCTURE\n{map_content.strip()}")

    # Skills/Tools
    skills_content = read_file_safe(os.path.join(BASE_DIR, "SKILLS.md"))
    if skills_content:
        parts.append(f"# YOUR TOOLS & SKILLS\n{skills_content.strip()}")

    # Custom skills from skills/ folder
    skills_dir = os.path.join(BASE_DIR, "skills")
    if os.path.isdir(skills_dir):
        custom_skills = [f for f in os.listdir(skills_dir) if f.endswith(".py")]
        if custom_skills:
            parts.append("# CUSTOM SKILLS AVAILABLE\n" + "\n".join(f"- `{s}`" for s in custom_skills))

    # Active environments
    env_file = os.path.join(BASE_DIR, "environments.json")
    if os.path.exists(env_file):
        try:
            envs = json.loads(read_file_safe(env_file))
            if envs:
                env_list = []
                for name, data in envs.items():
                    pkgs = ", ".join(data.get("packages", [])) or "None"
                    env_list.append(f"- **{name}** ({data['type']}): Packages: {pkgs}")
                parts.append("# ACTIVE ENVIRONMENTS\n" + "\n".join(env_list))
        except Exception:
            pass

    # Thinking mode
    if thinking_enabled:
        parts.append(
            "# RESPONSE MODE: THINKING ENABLED\n"
            "Think step-by-step inside [THINK]...[/THINK] blocks before answering.\n"
            "Give your final answer OUTSIDE the [THINK] blocks."
        )
    else:
        parts.append(
            "# RESPONSE MODE: DIRECT\n"
            "Respond directly and concisely. Do NOT use reasoning blocks or think tags."
        )

    return "\n\n".join(parts)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="new-agent-mohannad GUI server")
    parser.add_argument("--port", type=int, default=7777, help="Port to serve on")
    args = parser.parse_args()

    os.makedirs(GUI_DIR, exist_ok=True)
    server = HTTPServer(("127.0.0.1", args.port), AgentAPIHandler)
    log.info("GUI server running at http://localhost:%d", args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Server stopped.")

