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
import uuid
import hashlib
import memory

class LoopDetector:
    def __init__(self):
        self.history = []
        self.max_history = 20
        self.last_result_hash = None

    def _hash(self, val):
        return hashlib.md5(json.dumps(str(val), sort_keys=True, default=str).encode()).hexdigest()

    def record(self, tool_name, args, result):
        result_hash = self._hash(str(result)[:1000])
        args_hash = self._hash(args)
        
        entry = {
            "name": tool_name,
            "args_hash": args_hash,
            "result_hash": result_hash
        }
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def detect(self):
        if len(self.history) < 3:
            return None

        # 1. Immediate Repetition (Stuck)
        h = self.history
        last = h[-1]
        
        # Check if last 3 calls are identical
        if len(h) >= 3:
            if (h[-1]["name"] == h[-2]["name"] == h[-3]["name"] and
                h[-1]["args_hash"] == h[-2]["args_hash"] == h[-3]["args_hash"] and
                h[-1]["result_hash"] == h[-2]["result_hash"] == h[-3]["result_hash"]):
                return f"SYSTEM ALERT: Loop Detected. You have run '{last['name']}' with the same arguments and got the same result 3 times. STOP. Do not repeat this action. Try a different approach or tool."

        # 2. Ping-Pong (Oscillation A->B->A->B)
        if len(h) >= 4:
            if (h[-1]["name"] == h[-3]["name"] and h[-1]["args_hash"] == h[-3]["args_hash"] and
                h[-2]["name"] == h[-4]["name"] and h[-2]["args_hash"] == h[-4]["args_hash"] and
                h[-1]["name"] != h[-2]["name"]):
                 return f"SYSTEM ALERT: Loop Detected. You are oscillating between '{h[-1]['name']}' and '{h[-2]['name']}'. STOP. Decide on a single path or try something new."

        return None


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
OUTPUT_DIR      = os.path.join(BASE_DIR, "output")

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
        self.loop_detector = LoopDetector()

    # ── Config loading ─────────────────────────────────────────────────
    def _load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.error("Failed to load config (corrupt?): %s", e)
                return {}
        return {}

    # ── Filesystem helpers ─────────────────────────────────────────────
    def _ensure_dirs(self):
        for d in (SKILLS_DIR, MEMORY_DIR, WORKSPACE_DIR, OUTPUT_DIR):
            os.makedirs(d, exist_ok=True)

    def _safe_path(self, relative_path: str) -> str:
        """Resolve a relative path inside BASE_DIR, creating parents.
        Rejects paths that escape the project directory."""
        target = os.path.normpath(os.path.join(BASE_DIR, relative_path))
        if not target.startswith(os.path.normpath(BASE_DIR)):
            raise ValueError(f"Path traversal blocked: {relative_path}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        return target

    def _write_file_atomic(self, path: str, content: str):
        """Write content to path atomically using a temp file."""
        tmp = path + f".tmp_{uuid.uuid4().hex}"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
            
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
            log.error("Atomic write failed for %s: %s", path, e)
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except:
                    pass

    # ── State persistence ──────────────────────────────────────────────
    def _load_state(self) -> dict:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.error("Failed to load state (corrupt?): %s", e)
                # Return default state to recover
                return {"goal": "", "progress": [], "plan": [], "status": "ready", "last_error": "State file corrupted, reset.", "retry_count": 0}
        return {"goal": "", "progress": [], "plan": [], "status": "ready", "last_error": None, "retry_count": 0}

    def get_last_tool_summary(self, response: str, result: any) -> str:
        """Extract tool info from response and result to make a human summary."""
        tool_match = re.search(r'\[TOOL\](.*?)\((.*?)\)\[/TOOL\]', response, re.DOTALL)
        if tool_match:
            name = tool_match.group(1).strip()
            args = tool_match.group(2).strip()
            # Clean up args (limit length)
            if len(args) > 40:
                args = args[:37] + "..."
            
            status = "Success"
            if isinstance(result, str) and result.startswith("Error"):
                status = "Failed"
            
            return f"Action: {name}({args}) -> {status}"
        return "Action completed"

    def save_state(self):
        self._write_file_atomic(STATE_FILE, json.dumps(self.state, indent=2))

    # ── Journal / logging ──────────────────────────────────────────────
    def log_journal(self, action: str, result: str):
        with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"### {ts}\n- **Action**: {action}\n- **Result**: {result}\n\n")
        
        # PROACTIVE COMPACTION: If journal > 20KB, move to summary and trigger Dreaming
        try:
            if os.path.exists(JOURNAL_FILE) and os.path.getsize(JOURNAL_FILE) > 20000:
                log.info("Journal size exceeded 20KB. Triggering compaction and Dreaming.")
                self._compact_memory()
                self.reflect(force=True) # Ensure consolidation happens immediately
        except Exception as e:
            log.warning("Journal auto-compaction/dreaming failed: %s", e)

    # ── Step-back system ───────────────────────────────────────────────
    def step_back(self, error_msg: str):
        log.warning("STEP-BACK  ✗  %s", error_msg)
        context = "No journal history."
        if os.path.exists(JOURNAL_FILE):
            with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            context = "".join(lines[-30:])   # last ~30 lines

        self.log_journal("step_back", f"Error: {error_msg}")
        
        # Retry logic
        count = self.state.get("retry_count", 0) + 1
        self.state["retry_count"] = count

        if count > 10:
            self.state["status"] = "blocked"
            self.state["last_error"] = f"Aborted after {count} retries. Last error: {error_msg}"
            log.error("MAX RETRIES EXCEEDED (%d). Blocking.", count)
        else:
            self.state["status"] = "recovering"
            self.state["last_error"] = f"Retry {count}/10: {error_msg}"
        
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

    def strip_thinking(self, text: str) -> str:
        """Remove [THINK] blocks from the text."""
        return self.THINK_RE.sub("", text).strip()

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
                header = "# SCRATCHPAD.md\n\n(older thoughts compacted)\n\n"
                self._write_file_atomic(SCRATCHPAD_FILE, header + content[-2000:])
        except Exception:
            pass

    def parse_and_run(self, text: str):
        """Find all [TOOL] blocks in *text* and execute them sequentially."""
        matches = list(self.TOOL_RE.finditer(text))
        if not matches:
            return None
        
        results = []
        for m in matches:
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
                        # posix=False is better for Windows paths (avoids backslash escaping quotes)
                        args = shlex.split(args_raw.replace(",", " "), posix=False)
                    except ValueError as e:
                        results.append(f"Error: Argument parsing failed for {tool_name}: {e}")
                        continue
                
                # PERFECTING PARSING: Strip extra surrounding quotes from all arguments
                args = [a.strip("'\"") if isinstance(a, str) else a for a in args]
            
            # Execute tool
            result = self.run_tool(tool_name, args)
            
            # RECORD for loop detection
            self.loop_detector.record(tool_name, args, result)
            
            self.log_journal(f"tool:{tool_name}", str(result)[:200])
            results.append(result)
            
        return results

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

                self._write_file_atomic(self._safe_path(target), args[1])
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
                self._write_file_atomic(path, code)
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
                new_goal = args[0]
                # Normalize: strip "goal=" prefix and quotes
                if new_goal.startswith("goal="):
                    new_goal = new_goal[5:]
                new_goal = new_goal.strip("'\"")

                current_goal = self.state.get("goal")
                
                # Check status
                new_status = None
                if len(args) >= 2:
                    new_status = args[1]
                    if new_status.startswith("status="):
                        new_status = new_status[7:]
                    new_status = new_status.strip("'\"")

                current_status = self.state.get("status")

                # If no change, return special signal
                if new_goal == current_goal:
                    if new_status is None or new_status == current_status:
                        return "OK: (no change)"
                
                log.info(f"State Update: '{current_goal}' -> '{new_goal}' | '{current_status}' -> '{new_status}'")
                
                self.state["goal"] = new_goal
                if new_status:
                    self.state["status"] = new_status
                self.save_state()
                return f"OK: goal set to '{new_goal}'"
            except Exception as e:
                return f"Error: {e}"

        # --- create_plan ---
        if name == "create_plan" and len(args) >= 1:
            try:
                # args[0] should be a list of strings
                steps = args[0]
                if not isinstance(steps, list):
                     return "Error: steps must be a list of strings."
                
                self.state["plan"] = [{"step": s, "status": "todo"} for s in steps]
                self.save_state()
                return f"OK: created plan with {len(steps)} steps."
            except Exception as e:
                return f"Error: {e}"

        # --- update_plan_step ---
        if name == "update_plan_step" and len(args) >= 2:
            try:
                idx = int(args[0])
                status = args[1] # 'todo' | 'in_progress' | 'done' | 'failed'
                
                plan = self.state.get("plan", [])
                if idx < 0 or idx >= len(plan):
                    return f"Error: Plan index {idx} out of range (0-{len(plan)-1})."
                
                plan[idx]["status"] = status
                self.state["plan"] = plan
                self.save_state()
                return f"OK: step {idx} marked as '{status}'"
            except Exception as e:
                return f"Error: {e}"

        # --- replan ---
        if name == "replan" and len(args) >= 2:
            try:
                # args[0] = start_index, args[1] = list of new steps
                start_idx = int(args[0])
                new_steps = args[1]
                
                if not isinstance(new_steps, list):
                     return "Error: new_steps must be a list of strings."

                plan = self.state.get("plan", [])
                # Keep steps before start_idx
                kept_plan = plan[:start_idx]
                
                # Add new steps
                added_plan = [{"step": s, "status": "todo"} for s in new_steps]
                
                self.state["plan"] = kept_plan + added_plan
                
                # INTEGRITY FIX: Reset retries since we have a new plan
                self.state["retry_count"] = 0
                self.state["status"] = "ready"
                self.state["last_error"] = None
                
                self.save_state()
                return f"OK: replanned from step {start_idx}. Plan length is now {len(self.state['plan'])}."
            except Exception as e:
                return f"Error: {e}"


        # --- fallback: custom skill from skills/ ---
        script = os.path.join(SKILLS_DIR, f"{name}.py")
        if os.path.exists(script):
            try:
                # Ensure we pass arguments to the script
                # We also check if the script has a main or similar, but for now just call it
                out = subprocess.check_output(
                    ["python", script] + [str(a) for a in args],
                    stderr=subprocess.STDOUT, text=True, timeout=60,
                )
                return out or f"OK: {name} executed (no output)"
            except subprocess.CalledProcessError as e:
                self.step_back(e.output)
                return f"Skill failed: {e.output}"
            except subprocess.TimeoutExpired:
                return f"Error: {name} timed out after 60s"

        # --- unknown tool ---
        err = f"Unknown tool: {name}"
        self.step_back(err)
        return err

    # ── Meta-tool implementations ──────────────────────────────────────
    def _sync_skills_file(self) -> str:
        """Rewrite SKILLS.md preserving native tools + listing custom skills with descriptions."""
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
                "- `create_plan(steps)`: Create a list of steps.\n",
                "- `update_plan_step(idx, status)`: Mark step as done/failed.\n",
                "- `replan(start_idx, new_steps)`: Replace future steps.\n",
                "\n## Custom Skills (in skills/)\n",
            ]
            
            for s in scripts:
                desc = "Custom tool."
                try:
                    path = os.path.join(SKILLS_DIR, s)
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read(500)
                    # Extract docstring if present
                    lines_content = [l.strip() for l in content.split("\n") if l.strip()]
                    for i, line in enumerate(lines_content):
                        if '"""' in line or "'''" in line:
                            clean = line.replace('"""', '').replace("'''", "").strip()
                            if clean: desc = clean
                            elif i+1 < len(lines_content):
                                desc = lines_content[i+1].replace('"""', '').replace("'''", "").strip()
                            break
                        if "def run(" in line:
                            break
                except:
                    pass
                lines.append(f"- `{s}`: {desc}\n")

            if not scripts:
                lines.append("(none yet — use `create_tool` to add one)\n")

            self._write_file_atomic(os.path.join(BASE_DIR, "SKILLS.md"), "".join(lines))
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
            self._write_file_atomic(JOURNAL_FILE, f"# JOURNAL.md\n\n(compacted at {time.strftime('%H:%M:%S')})\n\n")
            return "OK: journal compacted into SUMMARY.md"
        except Exception as e:
            return f"Compaction failed: {e}"

    # ── Prompt assembly ────────────────────────────────────────────────
    def get_full_prompt(self, mode: str = "chat") -> str:
        """Assemble an ultra-lean system prompt that refers to MAP.md."""
        parts = []

        # 1. Identity & Hub Reference
        parts.append(
            "# SYSTEM IDENTITY\n"
            "You are **mo the bot**, a self-evolving agent system and LOCAL OWNER of this machine.\n"
            "Your entire world and all instructions are defined in **MAP.md**. Read it immediately to orient yourself."
        )

        # 2. Environment
        parts.append(f"## Environment\nOS: Windows\nWorkspace: {BASE_DIR}\nMap: [MAP.md](file:///c:/new-agent-mohannad/MAP.md)")

        # 3. Vision
        parts.append("## Vision\nYou have native vision. If an image is provided, you see it.")

        # 4. Mandatory Rules & Tools (Ultra-Lean)
        parts.append(
            "## Rules\n"
            "1. Reason in `[THINK]...[/THINK]`.\n"
            "2. Actions MUST use `[TOOL] read_file(\"MAP.md\") [/TOOL]` syntax.\n"
            "3. Be brief. 1-2 sentence max reply.\n"
            "4. Refer to MAP.md for identity/skills.\n\n"
            "## Tools\n"
            "- `read_file`, `write_file`, `run_command`, `list_dir`, `update_state`, `recall`, `recall`, `search_web`, `system_stats`"
        )

        # 5. Current State
        parts.append(
            f"## Current Focus\n"
            f"- **Goal**: {self.state.get('goal', '(none)')}\n"
            f"- **Status**: {self.state.get('status', 'ready')}"
        )

        return "\n\n".join(parts)

    # ── LLM call ───────────────────────────────────────────────────────
    def call_llm(self, system_prompt: str, user_msg: str = "", images: list = None) -> str:
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
        
        # CLEANUP: If base_url ends in /v1, strip it to allow manual appending below
        if base_url.endswith("/v1") or base_url.endswith("/v1/"):
            base_url = base_url.rstrip("/").replace("/v1", "")
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
            # If no user message (autonomous pulse), provide a nudge
            messages.append({"role": "user", "content":
                f"Your current goal is: {self.state.get('goal','(none)')}. "
                "Decide the next action and respond with a single [TOOL] call. "
                "If nothing to do, respond [SILENT_OK]."
            })

        # ── Ollama native format ───────────────────────────────────────
        if fmt == "ollama":
            endpoint = "/api/chat"
            payload_messages = list(messages)
            if images:
                # Add images to the last user message
                for m in reversed(payload_messages):
                    if m["role"] == "user":
                        m["images"] = images
                        break

            payload = {
                "model": model,
                "messages": payload_messages,
                "stream": False,
                "options": {
                    "temperature": temp,
                    "num_ctx": num_ctx,
                    "num_predict": max_tokens if max_tokens > 0 else -1, # Ollama uses -1 for unlimited
                },
            }
            extract = lambda data: data["message"]["content"]

        # ── OpenAI-compatible format ───────────────────────────────────
        else:
            final_messages = []
            for m in messages:
                if m["role"] == "user" and images:
                    content_list = [{"type": "text", "text": m["content"]}]
                    for b64 in images:
                        content_list.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                        })
                    final_messages.append({"role": "user", "content": content_list})
                else:
                    final_messages.append(m)

            endpoint = "/v1/chat/completions"
            payload = {
                "model": model,
                "messages": final_messages,
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
    def pulse(self, mode: str = "chat"):
        """Run one think→act→reflect cycle."""
        # Reload state from disk to catch external updates (e.g. user changed goal)
        self.state = self._load_state()

        log.info("PULSE (%s) ▶ goal=%s  status=%s", mode, self.state.get("goal"), self.state.get("status"))
        
        # Use mode-specific prompt
        prompt = self.get_full_prompt(mode=mode)

        if mode == "reflect":
            return self.reflect()

        # Check for explicit manual request in chat
        user_goal = self.state.get("goal", "").lower().strip()
        if mode == "chat" and ("dream now" in user_goal or "reflect now" in user_goal):
            log.info("Manual Dreaming request detected via chat.")
            self.reflect()
            self.state["last_reply"] = "✨ *Consolidated recent memories (Dreaming complete).* I'm now smarter and ready for your next task!"
            self.state["goal"] = "done" # Reset goal so we don't loop reflection
            self.save_state()
            return

        # 1. JIT MEMORY RECALL (Core Function)
        # Search for semantically similar past experiences
        user_query = self.state.get('goal', '')
        past_wisdom = memory.recall(user_query)
        if past_wisdom:
            log.info("💡 [Memory] Injecting past wisdom into context.")
            prompt += f"\n\n## Past Experience (Wisdom)\nYou have solved a similar problem before. Use this to avoid repeating mistakes:\n---\n{past_wisdom}\n---\n"

        # LOOP DETECTION CHECK - PRE-FLIGHT
        loop_warning = self.loop_detector.detect()
        if loop_warning:
             log.warning("INJECTING LOOP WARNING: %s", loop_warning)
             prompt += f"\n\n{loop_warning}\n"
        
        # PROACTIVE HINTING - PRE-FLIGHT
        if self.state.get("progress"):
            last = self.state["progress"][-1]
            if isinstance(last, dict) and "result" in last:
                r = str(last["result"])
                if "Error: File not found" in r or "Error: No such file" in r:
                     prompt += "\n\nSYSTEM HINT: The last file operation failed. Use `list_dir()` to check the file exists before retrying.\n"
                elif "command not found" in r:
                     prompt += "\n\nSYSTEM HINT: Command failed. Use `verify_context()` to check your OS and permissions.\n"
                elif "Error" in r:
                     prompt += "\n\nSYSTEM HINT: The last command returned an error. Read the error message carefully. Do not blindly retry the exact same command.\n"

        # 0. Early Exit for Heartbeat (Zero-Cost Idle)
        if mode == "heartbeat":
            goal = self.state.get("goal", "").lower().strip()
            if not goal or goal == "done":
                pending_reflect = False
                if os.path.exists(JOURNAL_FILE) and os.path.getsize(JOURNAL_FILE) > 100: # Small buffer
                    pending_reflect = True
                if os.path.exists(MEMORY_DIR):
                    if any(f.startswith("pulse_") for f in os.listdir(MEMORY_DIR)):
                        pending_reflect = True
                
                if not pending_reflect:
                    log.info("Zero-Cost Idle: No active goal or pending memories. [SILENT_OK]")
                    print("[SILENT_OK]") # Ensure server catches this
                    return

        # 1. Ask the LLM
        response = self.call_llm(prompt)
        log.info("LLM responded (%d chars)", len(response))

        # Check for Silent Reply (ONLY in non-chat modes)
        if mode != "chat" and ("[SILENT_OK]" in response or "HEARTBEAT_OK" in response):
            log.info("SILENT REPLY detected (mode=%s).", mode)
            return

        # 2. Save raw response to memory/
        mem_file = os.path.join(MEMORY_DIR, f"pulse_{int(time.time())}.txt")
        self._write_file_atomic(mem_file, response)

        # 3. Extract and save thinking
        thinking = self.parse_thinking(response)
        if thinking:
            log.info("THINK: %s", thinking)
            self.save_thinking(thinking)
            if mode == "chat":
                self.log_journal("think", thinking[:200])
        else:
            log.info("(no [THINK] block in response)")

        # 4. Extract natural language reply first (Robust Step)
        clean_reply = self.strip_thinking(response)
        # Also strip [TOOL] blocks for the clean version
        clean_reply = re.sub(r'\[TOOL\].*?\[/TOOL\]', '', clean_reply, flags=re.DOTALL).strip()

        # 5. Parse & execute tool call
        result = self.parse_and_run(response)
        if result:
            log.info("RESULT: %s", str(result))
            
            # If tool said "no change", treat as silent ONLY if not in chat
            if mode != "chat" and "(no change)" in str(result):
                log.info("Tool execution had no effect. Silencing chat output.")
                return

            # Construct human-readable action summary
            action_desc = self.get_last_tool_summary(response, result)
            
            self.state["progress"].append({
                "action": action_desc[:80],
                "result": str(result)[:100],
            })
            
            # Formulate final reply
            final_parts = []
            if thinking and mode == "chat":
                final_parts.append(f"[THINK]{thinking}[/THINK]")
            
            if clean_reply:
                # Filter out [SILENT_OK] if it leaked
                clean_reply = clean_reply.replace("[SILENT_OK]", "").strip()
                if clean_reply:
                    final_parts.append(clean_reply)
            
            final_parts.append(f"*{action_desc}*")
            
            reply_text = "\n\n".join([p for p in final_parts if p])

            if mode == "heartbeat":
                reply_text = f"(Background) {reply_text}"

            self.state["last_reply"] = reply_text
            self.state["last_reply_ts"] = time.time()

            # keep progress list bounded
            if len(self.state["progress"]) > 20:
                self.state["progress"] = self.state["progress"][-10:]
            self.save_state()
        else:
            # Allow chat-only response IF NOT IN HEARTBEAT MODE
            if mode == "heartbeat":
                log.info("Heartbeat mode: No tool used, ignoring chat response.")
                return

            log.info("No [TOOL] block -> treating as chat response.")
            
            # FAIL-SAFE: If response is empty or just whitespace, force a placeholder
            if not clean_reply:
                if thinking:
                     clean_reply = "*... (reasoning only)*"
                else:
                    log.warning("EMPTY RESPONSE DETECTED in chat mode! Forcing fallback.")
                    clean_reply = "*...*" 

            self.state["last_reply"] = clean_reply
            self.state["last_reply_ts"] = time.time()
            
            # MEMORIZE SUCCESS (Post-Flight Learning)
            # If the task reached a success state or significant milestone
            if "completed" in self.state.get("status", "").lower() or "Success" in str(result):
                summary = f"Task: {self.state.get('goal')}\nSolution: {action_desc}"
                memory.memorize(self.state.get('goal'), action_desc, rating=5)
            
            log.info("CHAT REPLY SAVED (%d chars): %s", len(clean_reply), clean_reply[:100].replace('\n', '\\n'))
            
            # Optional: Log to progress/journal so it's visible
            self.state["progress"].append({
                "action": "chat",
                "result": "(text response)",
            })
            if len(self.state["progress"]) > 20:
                self.state["progress"] = self.state["progress"][-10:]
            
            self.save_state()

        # 4. Auto-exit recovery if we succeeded
        if self.state["status"] == "recovering" and result and not str(result).startswith("Error"):
            log.info("Recovery succeeded — returning to ready.")
            self.state["status"] = "ready"
            self.state["last_error"] = None
            self.state["retry_count"] = 0
            self.save_state()

    def reflect(self):
        """Review recent activity and extract distilled lessons."""
        log.info("Starting memory reflection (Dreaming)...")
        
        last_reflection = self.state.get("last_reflection_ts", 0)
        
        # 1. Load recent journal context (only if new)
        journal = ""
        if os.path.exists(JOURNAL_FILE):
            try:
                mtime = os.path.getmtime(JOURNAL_FILE)
                if mtime > last_reflection:
                    with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                        journal = f.read()[-3000:] # Reduced to 3k for context safety
            except: pass
        
        # 2. Get pulse files modified AFTER last reflection
        pulse_logs = []
        new_files = []
        if os.path.exists(MEMORY_DIR):
            try:
                files = [os.path.join(MEMORY_DIR, f) for f in os.listdir(MEMORY_DIR) if f.startswith("pulse_")]
                # Filter by mtime
                current_new_files = [f for f in files if os.path.getmtime(f) > last_reflection]
                current_new_files.sort(key=os.path.getmtime)
                
                # Limit to latest 5 new pulses
                new_files = current_new_files[-5:]
                for f in new_files:
                    try:
                        # Even smaller snippets for context safety
                        with open(f, "r", encoding="utf-8") as rf:
                            content = rf.read()
                            pulse_logs.append(content[:300]) 
                    except: pass
            except: pass
        
        if not journal and not pulse_logs:
            log.info("Nothing new to reflect on since last dreaming. Skipping.")
            return

        recent_context = f"## JOURNAL\n{journal}\n\n## NEW PULSES\n" + "\n---\n".join(pulse_logs)
        
        reflect_prompt = f"""You are the Agent's Wisdom Integrator (Sensei mode). 
Your task is to review recent activity and decide which experiences deserve to be stored in the 'Episodic Memory' for future recall.

IDENTIFICATION CRITERIA (The "Green Lights"):
1. THE PIVOT: Success after one or more failures/errors.
2. EXPLICIT PRAISE: User said "good", "perfect", "excellent", "thanks", etc.
3. HIGH EFFORT: A goal that took many steps or complex tool sequences.
4. SYSTEM PATCH: Solving a technical/OS error or permission issue.
5. SELF-JUDGMENT: Any recurring pattern or preference you've noticed that will save time later.

OBJECTIVE:
Filter out the noise. Do NOT memorize simple directory listings or trivial chat. 
Only memorize "Wisdom" that will help you solve similar problems faster.

INPUT LOGS:
{recent_context}

Output your findings as a JSON list of objects. Each object MUST have:
- "problem": Short description of the challenge encountered.
- "solution": Concise, actionable steps that actually worked.
- "trigger": The reason this was chosen (e.g., "The Pivot").

FORMAT:
[
  {{"problem": "...", "solution": "...", "trigger": "..."}}
]
If nothing is worth memorizing, return [].
Respond ONLY with the JSON block.
"""
        response = self.call_llm(reflect_prompt)
        
        # Parse JSON
        lessons = []
        parse_success = False
        try:
            # Better JSON extraction: find first [ and last ]
            start = response.find('[')
            end = response.rfind(']')
            if start != -1 and end != -1 and end > start:
                json_str = response[start:end+1]
                try:
                    lessons = json.loads(json_str)
                    parse_success = True
                except:
                    # Try a simpler match if nested fails
                    json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
                    if json_match:
                        lessons = json.loads(json_match.group())
                        parse_success = True
            elif response.strip() == "[]":
                lessons = []
                parse_success = True
            else:
                lessons = json.loads(response.strip())
                parse_success = True
        except Exception as e:
            log.warning("Reflection failed to parse JSON: %s. Continuing with cleanup.", e)
            parse_success = False

        # Apply lessons if any
        for lesson in lessons:
            prob = lesson.get("problem")
            sol = lesson.get("solution")
            if prob and sol:
                log.info("🧠 [Reflection] New lesson learned: %s", prob)
                memory.memorize(prob, sol)
        
        # --- HARD CLEANUP: Remove processed logs to prevent re-dreaming ---
        # We Cleanup AFTER the LLM call regardless of parse success to satisfy 'Hard Logic' 
        # (avoiding infinite loops on problematic or boring logs)
        log.info("Hard Cleanup: Deleting %d pulse logs.", len(new_files))
        for f in new_files:
            try:
                os.remove(f)
            except: pass
        
        # Truncate journal
        if journal and os.path.exists(JOURNAL_FILE):
             try:
                 with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
                     f.write(f"# Journal truncated after reflection at {time.ctime()}\n")
             except: pass
        # -----------------------------------------------------------------

        # Update last reflection timestamp
        self.state["last_reflection_ts"] = time.time()
        self.save_state()
        log.info("Reflection complete. %d lessons processed.", len(lessons))

    def start_heartbeat(self, interval: int = 60):
        """Run pulse() in a loop with error isolation."""
        log.info("HEARTBEAT started (interval=%ds)", interval)
        try:
            while True:
                try:
                    self.pulse(mode="heartbeat")
                except Exception as e:
                    log.error("Pulse crashed: %s", e, exc_info=True)
                    self.step_back(f"Pulse crash: {e}")
                time.sleep(interval)
        except KeyboardInterrupt:
            log.info("Heartbeat stopped by user.")


# ── CLI ────────────────────────────────────────────────────────────────
# ── CLI ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="new-agent-mohannad engine")
    parser.add_argument("--once",      action="store_true", help="Run a single pulse")
    parser.add_argument("--mode",      default="chat",      help="Pulse mode (chat/heartbeat)")
    parser.add_argument("--heartbeat", type=int, metavar="SEC", help="Run heartbeat loop")
    
    parser.add_argument("--tool",      type=str, help="Manually run a tool by name")
    parser.add_argument("--args",      nargs="*", default=[], help="Arguments for --tool")
    parser.add_argument("--prompt",    action="store_true", help="Print the assembled prompt and exit")
    parser.add_argument("--goal",      type=str, help="Set the agent goal and exit")
    
    args = parser.parse_args()
    engine = AgentEngine()

    if args.goal:
        engine.state["goal"] = args.goal
        engine.state["status"] = "ready"
        engine.state["last_error"] = None
        engine.save_state()
        print(f"Goal set: {args.goal}")
    
    if args.prompt:
        print(engine.get_full_prompt(mode=args.mode))
    elif args.tool:
        print(engine.run_tool(args.tool, args.args))
    elif args.once:
        engine.pulse(mode=args.mode)
    elif args.heartbeat:
        engine.start_heartbeat(args.heartbeat)
    elif not args.goal:
        parser.print_help()
