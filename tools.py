"""
tools.py — Tool Registry
All tools Astra can use. Each takes a string input, returns a string result.
"""

import os
import webbrowser
import subprocess
import platform
from datetime import datetime
from duckduckgo_search import DDGS
from rag import search_rag, add_to_memory, get_memory_count, list_memories


# ─────────────────────────────────────────────
# TOOL IMPLEMENTATIONS
# ─────────────────────────────────────────────

def web_search(query: str) -> str:
    """Search the web with DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return "No results found."
        return "\n\n".join(
            f"[{r.get('title','Untitled')}]\n{r.get('body','')}"
            for r in results
        )
    except Exception as e:
        return f"Search failed: {e}"


def rag_search(query: str) -> str:
    """Search Astra's memory including learned conversations."""
    docs = search_rag(query)
    if not docs:
        return "Nothing in memory yet."
    return "\n\n".join(docs)


def open_app(app_name: str) -> str:
    """Open a desktop application."""
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(app_name)
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", app_name])
        else:
            subprocess.Popen([app_name])
        return f"Opened {app_name}."
    except Exception as e:
        return f"Could not open {app_name}: {e}"


def open_website(url: str) -> str:
    """Open a URL in the default browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}."


def create_file(filename: str, content: str) -> str:
    """Create a file with given content."""
    try:
        filename = filename.strip().strip('"').strip("'")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Created '{filename}' ({len(content)} chars)."
    except Exception as e:
        return f"Failed to create file: {e}"


def read_file(filename: str) -> str:
    """Read contents of a file."""
    filename = filename.strip().strip('"').strip("'")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        return content[:2000] + ("..." if len(content) > 2000 else "")
    except FileNotFoundError:
        return f"File '{filename}' not found."
    except Exception as e:
        return f"Failed to read: {e}"


def calculator(expression: str) -> str:
    """Evaluate a math expression safely."""
    allowed = set("0123456789+-*/().% ")
    if not all(c in allowed for c in expression):
        return "Invalid — only numbers and operators allowed."
    try:
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as e:
        return f"Calculation error: {e}"


def get_time(_: str = "") -> str:
    """Return current date and time."""
    return datetime.now().strftime("It is %A, %d %B %Y at %H:%M.")


def list_files(directory: str = ".") -> str:
    """List files in a directory."""
    directory = directory.strip() or "."
    try:
        entries = sorted(os.listdir(directory))
        return f"Files in '{directory}':\n" + "\n".join(entries)
    except Exception as e:
        return f"Could not list: {e}"


def remember(text: str) -> str:
    """Manually store a fact in memory."""
    try:
        add_to_memory(text, metadata={"type": "manual"})
        return f"Remembered: {text}"
    except Exception as e:
        return f"Failed to remember: {e}"


def recall_memory(query: str) -> str:
    """Search memory and return what Astra knows about a topic."""
    docs = search_rag(query, top_k=5)
    if not docs:
        return "I don't have any memories about that yet."
    return "Here's what I remember:\n" + "\n\n".join(docs)


def memory_stats(_: str = "") -> str:
    """Show how much Astra has learned."""
    count = get_memory_count()
    return f"I have {count} memories stored so far. I learn something new after every conversation!"


def forget_learned(_: str = "") -> str:
    """Clear all auto-learned memories (keep manual ones)."""
    from rag import clear_learned_memories
    clear_learned_memories()
    return "Cleared all learned memories. Manual memories are kept."


# ─────────────────────────────────────────────
# TOOL REGISTRY
# ─────────────────────────────────────────────
_REGISTRY = {
    "web_search":     (web_search,     "Search the internet for current information"),
    "rag_search":     (rag_search,     "Search Astra's memory and past conversations"),
    "open_app":       (open_app,       "Open a desktop application by name"),
    "open_website":   (open_website,   "Open a URL in the browser"),
    "create_file":    (create_file,    "Create a file — INPUT: filename, content"),
    "read_file":      (read_file,      "Read a file — INPUT: filename"),
    "calculator":     (calculator,     "Evaluate a math expression"),
    "get_time":       (get_time,       "Get current date and time"),
    "list_files":     (list_files,     "List files in a folder"),
    "remember":       (remember,       "Manually save a fact to memory"),
    "recall_memory":  (recall_memory,  "Search what Astra remembers about a topic"),
    "memory_stats":   (memory_stats,   "Show how many memories Astra has learned"),
    "forget_learned": (forget_learned, "Clear auto-learned memories"),
}

TOOLS            = {name: fn   for name, (fn, _)   in _REGISTRY.items()}
TOOL_DESCRIPTIONS = {name: desc for name, (_, desc) in _REGISTRY.items()}
