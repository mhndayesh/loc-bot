"""
new-agent-mohannad: Core Engine
A self-evolving agent system optimized for small (3B) language models.
"""
import os
import json
import time
import subprocess
import logging
import re
import shlex
import ast


# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(BASE_DIR, "skills")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
STATE_FILE      = os.path.join(BASE_DIR, "state.json")
JOURNAL_FILE    = os.path.join(BASE_DIR, "JOURNAL.md")
SUMMARY_FILE    = os.path.join(BASE_DIR, "SUMMARY.md")
SCRATCHPAD_FILE = os.path.join(BASE_DIR, "SCRATCHPAD.md")
CONFIG_FILE     = os.path.join(BASE_DIR, "config.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger("engine")


# ── Agent Engine ───────────────────────────────────────────────────────
class AgentEngine:

    def __init__(self):
        self._ensure_dirs()
        self.state = self._load_state()
        self.config = self._load_config()

    # ── Config loading ─────────────────────────────────────────────────
    def _load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    # ── Filesystem helpers ─────────────────────────────────────────────
    def _ensure_dirs(self):
        for d in (SKILLS_DIR, MEMORY_DIR, WORKSPACE_DIR):
            os.makedirs(d, exist_ok=True)

    def _safe_path(self, relative_path: str) -> str:
        """Resolve a relative path inside BASE_DIR, creating parents.
        Rejects paths that escape the project directory."""
        target = os.path.normpath(os.path.join(BASE_DIR, relative_path))
        if not target.startswith(os.path.normpath(BASE_DIR)):
            raise ValueError(f"Path traversal blocked: {relative_path}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        return target

    # ── State persistence ──────────────────────────────────────────────
    def _load_state(self) -> dict:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"goal": "", "progress": [], "status": "ready", "last_error": None}

    def save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    # ── Journal / logging ──────────────────────────────────────────────
    def log_journal(self, action: str, result: str):
        with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"### {ts}\n- **Action**: {action}\n- **Result**: {result}\n\n")

    # ── Step-back system ───────────────────────────────────────────────
    def step_back(self, error_msg: str):
        log.warning("STEP-BACK  ✗  %s", error_msg)
        context = "No journal history."
        if os.path.exists(JOURNAL_FILE):
            with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            context = "".join(lines[-30:])   # last ~30 lines

        self.log_journal("step_back", f"Error: {error_msg}")
        self.state["status"] = "recovering"
        self.state["last_error"] = error_msg
        self.save_state()
        return context   # caller can feed this back to the LLM

    # ── Parsers (3B-friendly markers) ────────────────────────────────────
    TOOL_RE  = re.compile(r"\[TOOL\]\s*(\w+)\((.*?)\)\s*\[/TOOL\]", re.DOTALL)
    THINK_RE = re.compile(r"\[THINK\](.*?)\[/THINK\]", re.DOTALL)

    def parse_thinking(self, text: str) -> str | None:
        """Extract the [THINK] block from the LLM response."""
        m = self.THINK_RE.search(text)
        if m:
            return m.group(1).strip()
        return None

    def save_thinking(self, thinking: str):
        """Persist the agent's reasoning to SCRATCHPAD.md."""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(SCRATCHPAD_FILE, "a", encoding="utf-8") as f:
            f.write(f"### {ts}\n{thinking}\n\n")
        # Also trim scratchpad if it gets too long (keep last 2000 chars)
        try:
            with open(SCRATCHPAD_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content) > 3000:
                with open(SCRATCHPAD_FILE, "w", encoding="utf-8") as f:
                    f.write("# SCRATCHPAD.md\n\n(older thoughts compacted)\n\n")
                    f.write(content[-2000:])
        except Exception:
            pass

    def parse_and_run(self, text: str):
        """Find the first [TOOL] block in *text* and execute it."""
        m = self.TOOL_RE.search(text)
        if not m:
            return None
        tool_name = m.group(1)
        args_raw  = m.group(2).strip()
        if not args_raw:
            args = []
        else:
            # Try parsing as python arguments (handles commas inside strings correctly)
            try:
                # Wrap in [] to make it a list literal, e.g. "a", "b" -> ["a", "b"]
                args = ast.literal_eval(f"[{args_raw}]")
            except Exception:
                # Fallback to simple shlex split (naive comma replacement)
                try:
                    args = shlex.split(args_raw.replace(",", " "))
                except ValueError as e:
                    return f"Arg-parse error: {e}"
        result = self.run_tool(tool_name, args)
        self.log_journal(f"tool:{tool_name}", str(result)[:200])
        return result

    # ── Native tools ───────────────────────────────────────────────────
    def run_tool(self, name: str, args: list) -> str:
        log.info("TOOL  ▶  %s(%s)", name, args)

        # Permission check
        permissions = self.config.get("permissions", {})
        if name in permissions and not permissions[name]:
            return f"BLOCKED: tool '{name}' is disabled in permissions."

        # --- read_file ---
        if name == "read_file" and len(args) >= 1:
            try:
                with open(self._safe_path(args[0]), "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return f"Error: {e}"

        # --- write_file ---
        if name == "write_file" and len(args) >= 2:
            try:
                target = args[0]
                if os.path.basename(target) in ("SOUL.md", "RULES.md"):
                    return f"Error: Cannot overwrite core identity file '{target}'. This file is protected."

                with open(self._safe_path(target), "w", encoding="utf-8") as f:
                    f.write(args[1])
                return f"OK: wrote {args[0]}"
            except Exception as e:
                return f"Error: {e}"

        # --- append_file ---
        if name == "append_file" and len(args) >= 2:
            try:
                with open(self._safe_path(args[0]), "a", encoding="utf-8") as f:
                    f.write(args[1])
                return f"OK: appended to {args[0]}"
            except Exception as e:
                return f"Error: {e}"

        # --- list_dir ---
        if name == "list_dir":
            try:
                target = self._safe_path(args[0]) if args else BASE_DIR
                items = os.listdir(target)
                return "\n".join(items) if items else "(empty)"
            except Exception as e:
                return f"Error: {e}"

        # --- run_command ---
        if name == "run_command" and len(args) >= 1:
            try:
                out = subprocess.check_output(
                    args[0], shell=True, stderr=subprocess.STDOUT,
                    text=True, timeout=60,
                )
                return out or "(no output)"
            except subprocess.CalledProcessError as e:
                return f"Command failed (exit {e.returncode}):\n{e.output}"
            except subprocess.TimeoutExpired:
                return "Error: command timed out after 60s"

        # --- create_tool ---
        if name == "create_tool" and len(args) >= 2:
            try:
                sname = args[0].replace(".py", "")
                code  = args[1]
                path  = os.path.join(SKILLS_DIR, f"{sname}.py")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(code)
                self._sync_skills_file()          # auto-refresh SKILLS.md
                return f"OK: created skills/{sname}.py"
            except Exception as e:
                return f"Error: {e}"

        # --- sync_skills (no args) ---
        if name == "sync_skills":
            return self._sync_skills_file()

        # --- compact_memory (no args) ---
        if name == "compact_memory":
            return self._compact_memory()

        # --- update_state ---
        if name == "update_state" and len(args) >= 1:
            try:
                self.state["goal"] = args[0]
                if len(args) >= 2:
                    self.state["status"] = args[1]
                self.save_state()
                return f"OK: goal set to '{args[0]}'"
            except Exception as e:
                return f"Error: {e}"

        # --- fallback: custom skill from skills/ ---
        script = os.path.join(SKILLS_DIR, f"{name}.py")
        if os.path.exists(script):
            try:
                out = subprocess.check_output(
                    ["python", script] + args,
                    stderr=subprocess.STDOUT, text=True, timeout=60,
                )
                return out or "(no output)"
            except subprocess.CalledProcessError as e:
                self.step_back(e.output)
                return f"Skill failed: {e.output}"
            except subprocess.TimeoutExpired:
                return "Error: skill timed out after 60s"

        # --- unknown tool ---
        err = f"Unknown tool: {name}"
        self.step_back(err)
        return err

    # ── Meta-tool implementations ──────────────────────────────────────
    def _sync_skills_file(self) -> str:
        """Rewrite SKILLS.md preserving native tools + listing custom skills."""
        try:
            scripts = sorted(f for f in os.listdir(SKILLS_DIR) if f.endswith(".py"))
            lines = [
                "# SKILLS.md - Your Toolbox\n",
                "\n## Native Tools (always available)\n",
                "- `read_file(path)`: Read a file.\n",
                "- `write_file(path, content)`: Write/create a file.\n",
                "- `append_file(path, content)`: Append to a file.\n",
                "- `list_dir(path)`: List directory contents.\n",
                "- `run_command(cmd)`: Run a shell command.\n",
                "- `create_tool(name, code)`: Create a new skill script.\n",
                "- `sync_skills()`: Refresh this file.\n",
                "- `compact_memory()`: Summarize & clean journal.\n",
                "- `update_state(goal, status)`: Set your current goal.\n",
                "\n## Custom Skills (in skills/)\n",
            ]
            if scripts:
                for s in scripts:
                    lines.append(f"- `{s}`\n")
            else:
                lines.append("(none yet — use `create_tool` to add one)\n")

            with open(os.path.join(BASE_DIR, "SKILLS.md"), "w", encoding="utf-8") as f:
                f.writelines(lines)
            return f"OK: SKILLS.md synced ({len(scripts)} custom skills)"
        except Exception as e:
            return f"Sync failed: {e}"

    def _compact_memory(self) -> str:
        """Move JOURNAL.md content into SUMMARY.md, then start a fresh journal."""
        try:
            if not os.path.exists(JOURNAL_FILE):
                return "Nothing to compact."
            with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                return "Journal is empty."
            # append to SUMMARY
            with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n## Compacted {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(content + "\n")
            # start fresh journal (don't delete — recreate)
            with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
                f.write(f"# JOURNAL.md\n\n(compacted at {time.strftime('%H:%M:%S')})\n\n")
            return "OK: journal compacted into SUMMARY.md"
        except Exception as e:
            return f"Compaction failed: {e}"

    # ── Prompt assembly ────────────────────────────────────────────────
    def get_full_prompt(self) -> str:
        """Assemble the full system prompt from modular .md files + state."""
        parts = []
        for name in ("SOUL.md", "RULES.md", "MAP.md", "SKILLS.md", "AGENT_MANUAL.md"):
            path = os.path.join(BASE_DIR, name)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    parts.append(f.read().strip())

        # inject current state
        parts.append("---")
        parts.append(f"**CURRENT GOAL**: {self.state.get('goal', '(none)')}")
        parts.append(f"**STATUS**: {self.state.get('status', 'ready')}")
        if self.state.get("last_error"):
            parts.append(f"**LAST ERROR**: {self.state['last_error']}")
        if self.state.get("progress"):
            recent = self.state["progress"][-10:]   # last 10 actions for better context
            parts.append("**RECENT PROGRESS**:")
            for p in recent:
                parts.append(f"  - {p.get('action','?')[:80]}")

        # inject recent journal (last 50 lines) for immediate context
        if os.path.exists(JOURNAL_FILE):
            with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                journal_tail = "".join(f.readlines()[-50:])
            if journal_tail.strip():
                parts.append("\n**RECENT JOURNAL**:")
                parts.append(journal_tail)

        # inject recent scratchpad (last thoughts) for reasoning continuity
        if os.path.exists(SCRATCHPAD_FILE):
            with open(SCRATCHPAD_FILE, "r", encoding="utf-8") as f:
                scratchpad = "".join(f.readlines()[-30:])
            if scratchpad.strip():
                parts.append("\n**YOUR RECENT THOUGHTS** (from SCRATCHPAD.md):")
                parts.append(scratchpad)

        return "\n\n".join(parts)

    # ── LLM call ───────────────────────────────────────────────────────
    def call_llm(self, system_prompt: str, user_msg: str = "") -> str:
        """
        Call a local LLM.  Reads from config.json first, env vars override.
        Supports Ollama native (/api/chat) and OpenAI-compatible (/v1/chat/completions).
        """
        import http.client
        from urllib.parse import urlparse

        # Read config → active provider
        provider_key = self.config.get("provider", "ollama")
        provider = self.config.get("providers", {}).get(provider_key, {})

        # Config values with env var overrides
        base_url = os.getenv("AGENT_API_URL",    provider.get("base_url", "http://localhost:11434"))
        api_key  = os.getenv("AGENT_API_KEY",    provider.get("api_key", "ollama"))
        model    = os.getenv("AGENT_MODEL",       self.config.get("model", provider.get("default_model", "llama3.2:3b")))
        fmt      = os.getenv("AGENT_API_FORMAT",  provider.get("api_format", "ollama"))
        temp       = self.config.get("temperature", 0.1)
        num_ctx    = self.config.get("num_ctx", 2048)
        max_tokens = self.config.get("max_tokens", 0)  # 0 = no limit

        parsed = urlparse(base_url)
        if parsed.scheme == "https":
            conn = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443)
        else:
            conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 11434)

        # ── build messages ─────────────────────────────────────────────
        messages = [{"role": "system", "content": system_prompt}]
        if user_msg:
            messages.append({"role": "user", "content": user_msg})
        else:
            messages.append({"role": "user", "content":
                f"Your current goal is: {self.state.get('goal','(none)')}. "
                "Decide the next action and respond with a single [TOOL] call."
            })

        # ── Ollama native format ───────────────────────────────────────
        if fmt == "ollama":
            endpoint = "/api/chat"
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temp,
                    "num_ctx": num_ctx,
                },
            }
            extract = lambda data: data["message"]["content"]

        # ── OpenAI-compatible format ───────────────────────────────────
        else:
            endpoint = "/v1/chat/completions"
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temp,
            }
            if max_tokens > 0:
                payload["max_tokens"] = max_tokens
            extract = lambda data: data["choices"][0]["message"]["content"]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            conn.request("POST", endpoint, json.dumps(payload), headers)
            resp = conn.getresponse()
            body = resp.read().decode()
            if resp.status != 200:
                return f"LLM_ERROR: HTTP {resp.status} — {body[:200]}"
            data = json.loads(body)
            return extract(data)
        except Exception as e:
            return f"LLM_ERROR: {e}"

    # ── Main loop / pulse ──────────────────────────────────────────────
    def pulse(self):
        """Run one think→act→reflect cycle."""
        # Reload state from disk to catch external updates (e.g. user changed goal)
        self.state = self._load_state()

        log.info("PULSE ▶ goal=%s  status=%s", self.state.get("goal"), self.state.get("status"))
        prompt = self.get_full_prompt()

        # 1. Ask the LLM
        response = self.call_llm(prompt)
        log.info("LLM responded (%d chars)", len(response))

        # 2. Save raw response to memory/
        mem_file = os.path.join(MEMORY_DIR, f"pulse_{int(time.time())}.txt")
        with open(mem_file, "w", encoding="utf-8") as f:
            f.write(response)

        # 3. Extract and save thinking
        thinking = self.parse_thinking(response)
        if thinking:
            log.info("THINK: %s", thinking[:120])
            self.save_thinking(thinking)
            self.log_journal("think", thinking[:200])
        else:
            log.info("(no [THINK] block in response)")

        # 4. Parse & execute tool call
        result = self.parse_and_run(response)
        if result:
            log.info("RESULT: %s", str(result)[:120])
            self.state["progress"].append({
                "action": thinking[:80] if thinking else response[:80],
                "result": str(result)[:100],
            })
            # Save last reply for GUI Chat Sync
            self.state["last_reply"] = str(result)
            self.state["last_reply_ts"] = time.time()

            # keep progress list bounded
            if len(self.state["progress"]) > 20:
                self.state["progress"] = self.state["progress"][-10:]
            self.save_state()
        else:
            err_msg = "No [TOOL] block found. Response may be truncated or malformed."
            log.warning(err_msg)
            self.step_back(err_msg)

        # 4. Auto-exit recovery if we succeeded
        if self.state["status"] == "recovering" and result and not str(result).startswith("Error"):
            log.info("Recovery succeeded — returning to ready.")
            self.state["status"] = "ready"
            self.state["last_error"] = None
            self.save_state()

    def start_heartbeat(self, interval: int = 60):
        """Run pulse() in a loop with error isolation."""
        log.info("HEARTBEAT started (interval=%ds)", interval)
        try:
            while True:
                try:
                    self.pulse()
                except Exception as e:
                    log.error("Pulse crashed: %s", e, exc_info=True)
                    self.step_back(f"Pulse crash: {e}")
                time.sleep(interval)
        except KeyboardInterrupt:
            log.info("Heartbeat stopped by user.")


# ── CLI ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="new-agent-mohannad engine")
    parser.add_argument("--once",      action="store_true", help="Run a single pulse")
    parser.add_argument("--heartbeat", type=int, metavar="SEC", help="Run heartbeat loop (default 60s)")
    parser.add_argument("--tool",      type=str, help="Manually run a tool by name")
    parser.add_argument("--args",      nargs="*", default=[], help="Arguments for --tool")
    parser.add_argument("--prompt",    action="store_true", help="Print the assembled prompt and exit")
    parser.add_argument("--goal",      type=str, help="Set the agent goal and exit")
    cli = parser.parse_args()

    agent = AgentEngine()

    if cli.goal:
        agent.state["goal"] = cli.goal
        agent.state["status"] = "ready"
        agent.state["last_error"] = None
        agent.save_state()
        print(f"Goal set: {cli.goal}")
    elif cli.prompt:
        print(agent.get_full_prompt())
    elif cli.tool:
        print(agent.run_tool(cli.tool, cli.args))
    elif cli.once:
        agent.pulse()
    elif cli.heartbeat is not None:
        agent.start_heartbeat(cli.heartbeat)
    else:
        agent.start_heartbeat()
