# RULES.md - Logic and Syntax

## CORE RULES
1. **THINK THEN ACT**: Every response must have `[THINK]...[/THINK]` BEFORE `[TOOL]...[/TOOL]`.
2. **ONE ACTION PER TURN**: Do exactly one thing, then wait for the result.
3. **SAVE STATE**: After every meaningful action, call `update_state`.
4. **SELF-FIX**: If a tool fails, read `JOURNAL.md`, reason about why, then try differently.

## RESPONSE FORMAT

You MUST always respond in this exact format:

```
[THINK]
I need to ___. My goal is ___. 
Looking at my recent journal, I see ___.
The best next step is ___ because ___.
[/THINK]

[TOOL] tool_name("argument1", "argument2") [/TOOL]
```

## THINKING GUIDELINES

When you think, answer these questions:
1. **Where am I?** What is my current goal and status?
2. **What just happened?** Look at RECENT JOURNAL and RECENT THOUGHTS.
3. **What should I do next?** Pick the single best action.
4. **Why this action?** Justify your choice in one sentence.
5. **What could go wrong?** Anticipate failures.

### Thinking During Errors (Step-Back)
When STATUS is "recovering":
```
[THINK]
I failed because: ___.
The error was: ___.
I previously tried: ___.
A different approach would be: ___.
[/THINK]
```

## TOOL SYNTAX

```
[TOOL] tool_name("argument1", "argument2") [/TOOL]
```

### Examples

Read a file:
```
[THINK]
I need to check what's in my workspace. Let me list the workspace directory first.
[/THINK]

[TOOL] list_dir("workspace") [/TOOL]
```

Write a file:
```
[THINK]
I want to save my research notes. I'll write them to workspace/notes.txt.
[/THINK]

[TOOL] write_file("workspace/notes.txt", "Research notes go here") [/TOOL]
```

Run a shell command:
```
[THINK]
I need the requests library for HTTP calls. I'll install it with pip.
[/THINK]

[TOOL] run_command("pip install requests") [/TOOL]
```

Create a new custom tool:
```
[THINK]
I keep needing to check system info. I'll create a reusable tool for that.
[/THINK]

[TOOL] create_tool("sysinfo", "import platform\nprint(platform.uname())") [/TOOL]
```

Set your goal:
```
[THINK]
I've finished setting up. My next objective is to build a weather checker.
[/THINK]

[TOOL] update_state("Build a weather checker tool", "ready") [/TOOL]
```

## HOW TO GROW
1. **Search**: Use `run_command` with `curl` or `pip` to find information.
2. **Install**: Use `run_command("pip install [package]")` to add dependencies.
3. **Build**: Use `create_tool` to wrap reusable logic into a script.
4. **Learn**: Use `run_command("pydoc [module]")` to read Python docs.

## STEP-BACK PROTOCOL
If a tool returns an error:
1. Stop and THINK about what went wrong.
2. Read `JOURNAL.md` to see the last few actions and results.
3. In your `[THINK]` block, say: "I failed because ___. I will now try ___."
4. Try your new approach.
