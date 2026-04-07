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


# ─────────────────────────────────────────────
# AWS EC2 TOOLS — auto-registered if boto3 available
# ─────────────────────────────────────────────
try:
    from aws_tools import AWS_TOOLS
    for name, (fn, desc) in AWS_TOOLS.items():
        _REGISTRY[name] = (fn, desc)
    TOOLS             = {name: fn   for name, (fn, _)   in _REGISTRY.items()}
    TOOL_DESCRIPTIONS = {name: desc for name, (_, desc) in _REGISTRY.items()}
    print(f"[Tools] AWS EC2 tools loaded: {list(AWS_TOOLS.keys())}")
except ImportError:
    print("[Tools] boto3 not installed — AWS tools disabled. Run: pip install boto3")
except Exception as e:
    print(f"[Tools] AWS tools failed to load: {e}")


def improvement_stats(_: str = "") -> str:
    """Show Astra's self-improvement progress."""
    from self_improve import get_improvement_stats
    return get_improvement_stats()


def self_reflect(_: str = "") -> str:
    """Astra analyzes her own performance and improves."""
    from self_improve import analyze_performance
    return analyze_performance()


def teach_new_tool(description: str) -> str:
    """Teach Astra a new skill by describing it."""
    from self_improve import create_new_tool
    return create_new_tool(description)


# Add new tools to registry
TOOLS["improvement_stats"] = improvement_stats
TOOLS["self_reflect"]      = self_reflect
TOOLS["teach_new_tool"]    = teach_new_tool
TOOL_DESCRIPTIONS["improvement_stats"] = "Show Astra self-improvement progress and stats"
TOOL_DESCRIPTIONS["self_reflect"]      = "Astra reflects on performance and improves herself"
TOOL_DESCRIPTIONS["teach_new_tool"]    = "Teach Astra a new skill — INPUT: description of the tool"


def learning_stats(_: str = "") -> str:
    """Show Astra's autonomous learning statistics."""
    from self_learn import get_learning_stats
    return get_learning_stats()


def skill_library(_: str = "") -> str:
    """Show all skills Astra has autonomously created."""
    from self_learn import get_skill_library
    return get_skill_library()


def task_patterns(_: str = "") -> str:
    """Analyse patterns in Astra's task performance."""
    from self_learn import analyze_task_patterns
    return analyze_task_patterns()


TOOLS["learning_stats"] = learning_stats
TOOLS["skill_library"]  = skill_library
TOOLS["task_patterns"]  = task_patterns
TOOL_DESCRIPTIONS["learning_stats"] = "Show autonomous self-learning stats and progress"
TOOL_DESCRIPTIONS["skill_library"]  = "Show all skills Astra created autonomously"
TOOL_DESCRIPTIONS["task_patterns"]  = "Analyse what types of tasks Astra performs best"


def health_check(_: str = "") -> str:
    """Run Astra full system health check."""
    from self_repair import run_health_check
    report = run_health_check()
    healthy  = len(report["healthy"])
    errors   = len(report["errors"])
    warnings = len(report["warnings"])
    return (f"Health check complete. {healthy} modules healthy, "
            f"{errors} errors, {warnings} warnings.")

def repair_history(_: str = "") -> str:
    """Show Astra self-repair history."""
    from self_repair import get_repair_history
    return get_repair_history()

def list_backups(_: str = "") -> str:
    """List available file backups."""
    from self_repair import list_backups as _lb
    return _lb()

def rollback(filename: str) -> str:
    """Rollback a file to its previous backup version."""
    from self_repair import rollback_file
    success = rollback_file(filename.strip())
    return f"Rollback {'successful' if success else 'failed'} for {filename}."

TOOLS["health_check"]   = health_check
TOOLS["repair_history"] = repair_history
TOOLS["list_backups"]   = list_backups
TOOLS["rollback"]       = rollback
TOOL_DESCRIPTIONS["health_check"]   = "Run a full health check on all Astra modules"
TOOL_DESCRIPTIONS["repair_history"] = "Show history of all self-repairs Astra has performed"
TOOL_DESCRIPTIONS["list_backups"]   = "List all available file backups"
TOOL_DESCRIPTIONS["rollback"]       = "Rollback a file to previous version — INPUT: filename"


def owner_info(_: str = "") -> str:
    """Show current Astra owner information."""
    from ownership import get_owner_info
    return get_owner_info()

def transfer_history(_: str = "") -> str:
    """Show ownership transfer history."""
    from ownership import get_transfer_history
    return get_transfer_history()

TOOLS["owner_info"]        = owner_info
TOOLS["transfer_history"]  = transfer_history
TOOL_DESCRIPTIONS["owner_info"]       = "Show who currently owns Astra"
TOOL_DESCRIPTIONS["transfer_history"] = "Show history of ownership transfers"
