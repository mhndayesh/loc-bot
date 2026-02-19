# Web Interaction & Search Protocols

## Browser-less Browsing (`browser.py`)
Since you do not have a GUI browser available for agentic use, you rely on the `browser.py` skill, which uses the `requests` library.

### 1. Request Protocol
- **User-Agent**: Always uses a modern Chrome/Windows User-Agent to avoid immediate blocklisting.
- **Headers**: Includes `Accept` and `Accept-Language` headers to mimic a real browser profile.
- **Timeout**: Hardcoded to 15 seconds to prevent the engine from hanging on unresponsive sites.

### 2. Content Extraction
- The tool automatically strips `<script>`, `<style>`, and all HTML tags.
- It returns a clean text preview (first 2000 characters).
- **CAPTCHA Detection**: It scans the HTML for keywords like "captcha" or "robot check" and returns a `BLOCKED` status if found.

## Web Search (`search_web.py`)
This tool uses DuckDuckGo's HTML-only interface, which requires no API keys and is extremely robust.

### 1. Query Strategies
- **Broad**: "python subprocess tutorial"
- **Specific**: "site:stackoverflow.com FileNotFoundError Windows"
- **Internal**: Use this to find documentation for libraries you've just installed.

### 2. Handling Results
- `search_web` returns a list of snippets and URLs.
- **Workflow**:
    1. Search for a topic.
    2. Pick the most relevant URL.
    3. Call `browser(url)` to read the full content.

## Recovery Actions
- **If Blocked**: Try a different search query or a different source.
- **No Results**: Check if your machine has internet access via `run_command("ping 8.8.8.8")`.
- **Truncated Info**: If 2000 characters isn't enough, create a custom script to fetch specific chunks of the URL if needed, but usually the summary is sufficient.
