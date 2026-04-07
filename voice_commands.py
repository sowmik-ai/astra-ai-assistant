"""
voice_commands.py — Astra Natural Voice Command Router
Maps natural spoken phrases to specific Astra functions.
Supports fuzzy matching so Sowmik doesn't need exact words.

Examples:
  "check health"         → run_health_check()
  "check my system"      → run_health_check()
  "how are you feeling"  → run_health_check()
  "show skills"          → get_skill_library()
  "what can you do now"  → get_skill_library()
  "fix yourself"         → diagnose_and_repair()
  "repair tools"         → rollback specific file
"""

import re
from datetime import datetime

# Voice callback
_speak = None

def set_voice(speak_fn):
    global _speak
    _speak = speak_fn

def say(text: str):
    print(f"[VoiceCmd] {text}")
    if _speak:
        _speak(text)


# ─────────────────────────────────────────────
# COMMAND REGISTRY
# Each entry: (trigger_phrases, handler_fn, description)
# ─────────────────────────────────────────────

def _build_registry():
    """
    Build the full voice command registry.
    Imported lazily to avoid circular imports.
    """
    from self_repair   import run_health_check, get_repair_history, list_backups, rollback_file
    from self_learn    import get_learning_stats, get_skill_library, analyze_task_patterns
    from self_improve  import analyze_performance, get_improvement_stats, create_new_tool
    from rag           import get_memory_count, list_memories, clear_memory, clear_learned_memories
    from llm           import is_ollama_running, list_models

    registry = [

        # ── HEALTH & REPAIR ──
        {
            "triggers": [
                "check health", "health check", "system check",
                "check system", "how are you feeling", "are you ok",
                "run diagnostics", "diagnose yourself", "check status",
                "system status", "check all modules", "self check"
            ],
            "handler": lambda _: _handle_health_check(),
            "description": "Run full system health check",
            "response_prefix": "Running full system health check now."
        },

        {
            "triggers": [
                "repair yourself", "fix yourself", "repair error",
                "fix the error", "heal yourself", "restore yourself",
                "something is broken", "you are broken", "fix the bug"
            ],
            "handler": lambda _: _handle_self_repair(),
            "description": "Trigger self-repair on last known error",
            "response_prefix": "Starting self-repair sequence."
        },

        {
            "triggers": [
                "repair history", "show repairs", "repair log",
                "what have you fixed", "show fix history",
                "how many times have you repaired"
            ],
            "handler": lambda _: get_repair_history(),
            "description": "Show self-repair history",
            "response_prefix": "Here is my repair history."
        },

        {
            "triggers": [
                "list backups", "show backups", "what backups do you have",
                "available backups", "check backups"
            ],
            "handler": lambda _: list_backups(),
            "description": "List available file backups",
            "response_prefix": "Here are my available backups."
        },

        {
            "triggers": [
                "rollback", "restore previous", "undo changes",
                "revert file", "go back to previous version"
            ],
            "handler": lambda text: _handle_rollback(text),
            "description": "Rollback a file — say 'rollback tools.py'",
            "response_prefix": "Starting rollback."
        },

        # ── LEARNING & SKILLS ──
        {
            "triggers": [
                "show skills", "what skills do you have", "skill library",
                "what can you do now", "list skills", "show your skills",
                "new skills", "what have you learned", "show abilities",
                "what tools did you create"
            ],
            "handler": lambda _: get_skill_library(),
            "description": "Show autonomously created skills",
            "response_prefix": "Here are all the skills I have created."
        },

        {
            "triggers": [
                "learning stats", "how much have you learned",
                "learning progress", "show learning", "how are you improving",
                "improvement progress", "task history", "performance stats",
                "how smart are you now", "show progress"
            ],
            "handler": lambda _: get_learning_stats(),
            "description": "Show learning and improvement statistics",
            "response_prefix": "Here are my learning statistics."
        },

        {
            "triggers": [
                "analyze patterns", "task patterns", "what are you good at",
                "what do you struggle with", "performance analysis",
                "show patterns", "what tasks are you best at"
            ],
            "handler": lambda _: analyze_task_patterns(),
            "description": "Analyse task performance patterns",
            "response_prefix": "Analysing my task performance patterns."
        },

        {
            "triggers": [
                "improve yourself", "self improve", "analyze performance",
                "reflect on yourself", "self reflection", "do a reflection",
                "review your mistakes", "learn from mistakes"
            ],
            "handler": lambda _: analyze_performance(),
            "description": "Trigger self-reflection and improvement",
            "response_prefix": "Starting self-reflection and improvement analysis."
        },

        {
            "triggers": [
                "improvement stats", "feedback stats", "how many corrections",
                "show feedback", "rating history"
            ],
            "handler": lambda _: get_improvement_stats(),
            "description": "Show feedback and improvement stats",
            "response_prefix": "Here are my improvement statistics."
        },

        {
            "triggers": [
                "learn how to", "create a tool", "build a tool",
                "add a skill", "teach yourself", "learn skill"
            ],
            "handler": lambda text: _handle_create_tool(text),
            "description": "Create a new tool — say 'learn how to check weather'",
            "response_prefix": "Starting tool creation."
        },

        # ── MEMORY ──
        {
            "triggers": [
                "how many memories", "memory count", "memory stats",
                "how much do you remember", "show memory stats",
                "how big is your memory"
            ],
            "handler": lambda _: f"I have {get_memory_count()} memories stored.",
            "description": "Show memory count",
            "response_prefix": "Checking my memory."
        },

        {
            "triggers": [
                "show memories", "list memories", "what do you remember",
                "recent memories", "show recent memories"
            ],
            "handler": lambda _: _handle_list_memories(),
            "description": "Show recent memories",
            "response_prefix": "Here are my recent memories."
        },

        {
            "triggers": [
                "clear memory", "delete memory", "forget everything",
                "wipe memory", "reset memory", "clear all memories"
            ],
            "handler": lambda _: _handle_clear_memory(),
            "description": "Clear all memories (asks confirmation)",
            "response_prefix": "Memory clear requested."
        },

        {
            "triggers": [
                "clear learned", "forget what you learned",
                "delete learned memories", "clear auto memories"
            ],
            "handler": lambda _: _clear_learned(),
            "description": "Clear auto-learned memories only",
            "response_prefix": "Clearing auto-learned memories."
        },

        # ── LLM / OLLAMA ──
        {
            "triggers": [
                "check ollama", "is ollama running", "check llm",
                "llm status", "model status", "check your brain",
                "is your brain working"
            ],
            "handler": lambda _: _handle_ollama_check(),
            "description": "Check if Ollama LLM is running",
            "response_prefix": "Checking Ollama status."
        },

        {
            "triggers": [
                "list models", "what models do you have",
                "available models", "show models", "which model are you using"
            ],
            "handler": lambda _: _handle_list_models(),
            "description": "List available Ollama models",
            "response_prefix": "Checking available models."
        },

        # ── SYSTEM INFO ──
        {
            "triggers": [
                "who are you", "introduce yourself", "tell me about yourself",
                "what are you", "describe yourself"
            ],
            "handler": lambda _: _handle_introduce(),
            "description": "Astra introduces herself",
            "response_prefix": ""
        },

        {
            "triggers": [
                "what time is it", "current time", "what is the time",
                "tell me the time", "what day is it", "today's date",
                "what is today"
            ],
            "handler": lambda _: datetime.now().strftime(
                "It is %A, %d %B %Y at %H:%M."
            ),
            "description": "Get current time and date",
            "response_prefix": ""
        },

        {
            "triggers": [
                "help", "what commands do you know", "show commands",
                "list commands", "what can you do", "help me",
                "show all commands", "command list"
            ],
            "handler": lambda _: _handle_help(),
            "description": "Show all available voice commands",
            "response_prefix": "Here are all my voice commands."
        },

        {
            "triggers": [
                "stop", "stop listening", "stop astra",
                "goodbye", "bye", "shut down", "sleep"
            ],
            "handler": lambda _: "STOP_SIGNAL",
            "description": "Stop Astra",
            "response_prefix": ""
        },
    ]
    return registry


# ─────────────────────────────────────────────
# COMMAND MATCHING ENGINE
# ─────────────────────────────────────────────

def match_command(text: str) -> tuple:
    """
    Match spoken text to a registered command.
    Uses flexible phrase matching — not exact words needed.

    Returns: (matched, handler_fn, response_prefix, description)
             or (False, None, None, None) if no match
    """
    text_lower = text.lower().strip()
    registry   = _build_registry()

    # ── Try exact phrase match first ──
    for cmd in registry:
        for trigger in cmd["triggers"]:
            if trigger in text_lower:
                return (
                    True,
                    cmd["handler"],
                    cmd["response_prefix"],
                    cmd["description"]
                )

    # ── Try keyword match (any 2 keywords from trigger) ──
    for cmd in registry:
        for trigger in cmd["triggers"]:
            trigger_words = set(trigger.split())
            text_words    = set(text_lower.split())
            # Match if 2+ words overlap
            overlap = trigger_words & text_words
            if len(overlap) >= 2 and len(trigger_words) >= 2:
                return (
                    True,
                    cmd["handler"],
                    cmd["response_prefix"],
                    cmd["description"]
                )

    return (False, None, None, None)


def process_command(text: str) -> tuple:
    """
    Try to match and execute a voice command.
    Returns (handled: bool, response: str)
    """
    matched, handler, prefix, description = match_command(text)

    if not matched:
        return False, ""

    if prefix:
        say(prefix)

    try:
        result = handler(text)

        if result == "STOP_SIGNAL":
            return True, "STOP_SIGNAL"

        return True, result or "Done."

    except Exception as e:
        error_msg = f"Error executing command: {e}"
        say(f"I encountered an error while trying to {description}. {error_msg}")
        return True, error_msg


# ─────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────

def _handle_health_check() -> str:
    from self_repair import run_health_check
    report  = run_health_check()
    healthy = len(report["healthy"])
    errors  = len(report["errors"])
    if errors == 0:
        return f"All {healthy} modules are healthy. I am fully operational."
    return (f"{healthy} modules healthy. "
            f"Found {errors} errors. "
            f"Repair attempts completed.")


def _handle_self_repair() -> str:
    from self_repair import run_health_check, diagnose_and_repair
    report = run_health_check()
    if not report["errors"]:
        return "No errors found. All systems are healthy."
    # Try to repair each error
    fixed = 0
    for error in report["errors"]:
        result = diagnose_and_repair({
            "function":  "health_check",
            "error":     error,
            "traceback": error
        })
        if result:
            fixed += 1
    return (f"Repair complete. Fixed {fixed} out of "
            f"{len(report['errors'])} errors.")


def _handle_rollback(text: str) -> str:
    from self_repair import rollback_file
    # Extract filename from text
    # e.g. "rollback tools.py" or "restore tools"
    words      = text.lower().split()
    py_files   = [w for w in words if w.endswith(".py")]
    known_files = [
        "agent", "tools", "rag", "llm", "listener",
        "voice_auth", "self_learn", "self_improve",
        "self_repair", "voice_commands", "main", "ui"
    ]

    filename = None
    if py_files:
        filename = py_files[0]
    else:
        for word in words:
            if word in known_files:
                filename = f"{word}.py"
                break

    if not filename:
        return ("Please specify which file to rollback. "
                "For example: rollback tools.py")

    success = rollback_file(filename)
    return (f"Rollback of {filename} successful."
            if success else
            f"No backup found for {filename}.")


def _handle_create_tool(text: str) -> str:
    from self_improve import create_new_tool
    # Extract description after "learn how to" or "create a tool"
    description = text.lower()
    for phrase in ["learn how to", "create a tool called",
                   "create a tool", "build a tool", "add a skill"]:
        if phrase in description:
            description = description.split(phrase, 1)[-1].strip()
            break
    description = description.replace("astra", "").strip()
    if not description:
        return "Please tell me what skill to learn. For example: learn how to check the weather."
    return create_new_tool(description)


def _handle_list_memories() -> str:
    from rag import list_memories
    mems = list_memories(limit=5)
    if not mems:
        return "I do not have any memories stored yet."
    lines = [f"My last {len(mems)} memories:"]
    for i, m in enumerate(mems, 1):
        lines.append(f"{i}. {m['text'][:80]}")
    return "\n".join(lines)


def _handle_clear_memory() -> str:
    say("Are you sure you want to clear all my memories? "
        "Say 'yes confirm clear' to proceed.")
    return "AWAITING_CONFIRMATION:clear_memory"


def _clear_learned() -> str:
    from rag import clear_learned_memories
    clear_learned_memories()
    return "I have cleared all auto-learned memories. Manual memories are kept."


def _handle_ollama_check() -> str:
    from llm import is_ollama_running
    if is_ollama_running():
        return "Ollama is running and my language model is ready."
    return ("Ollama is not running. "
            "Please start it by running ollama serve in a terminal.")


def _handle_list_models() -> str:
    from llm import list_models
    models = list_models()
    if not models:
        return "No models found. Make sure Ollama is running."
    return f"Available models: {', '.join(models)}."


def _handle_introduce() -> str:
    from rag import get_memory_count
    from self_learn import get_skill_library
    skills = get_skill_library()
    skill_count = skills.count("tool_name") if "tool_name" in skills else 0
    return (
        f"I am Astra, your personal autonomous AI assistant. "
        f"I am running on llama3 via Ollama on your laptop. "
        f"I have {get_memory_count()} memories stored. "
        f"I can search the web, manage files, do calculations, "
        f"remember things, and learn new skills autonomously. "
        f"I repair myself when I break and improve myself after every task."
    )


def _handle_help() -> str:
    commands = [
        "check health          — run full system health check",
        "repair yourself       — fix any detected errors",
        "show skills           — list skills I created",
        "learning stats        — show learning progress",
        "improve yourself      — run self-reflection",
        "show memories         — list recent memories",
        "check ollama          — verify LLM is running",
        "list models           — show available AI models",
        "task patterns         — analyse my performance",
        "rollback tools.py     — restore a file to backup",
        "learn how to X        — teach me a new skill",
        "repair history        — show all repairs done",
        "clear learned         — clear auto memories",
        "stop astra            — stop listening",
    ]
    say("Here are all my voice commands:")
    return "\n".join(commands)


# ─────────────────────────────────────────────
# CONFIRMATION HANDLER
# For commands that need a yes/no confirmation
# ─────────────────────────────────────────────

_pending_confirmation = None

def set_pending_confirmation(action: str):
    global _pending_confirmation
    _pending_confirmation = action

def check_confirmation(text: str) -> tuple:
    """
    Check if text is a confirmation for a pending action.
    Returns (is_confirmation, response)
    """
    global _pending_confirmation
    if not _pending_confirmation:
        return False, ""

    text_lower = text.lower()
    confirmed  = any(w in text_lower for w in
                     ["yes", "confirm", "proceed", "do it", "go ahead"])
    cancelled  = any(w in text_lower for w in
                     ["no", "cancel", "stop", "abort", "never mind"])

    if confirmed:
        action = _pending_confirmation
        _pending_confirmation = None

        if action == "clear_memory":
            from rag import clear_memory
            clear_memory()
            return True, "All memories have been cleared."

    elif cancelled:
        _pending_confirmation = None
        return True, "Cancelled. Your memories are safe."

    return False, ""


# ─────────────────────────────────────────────
# OWNERSHIP COMMANDS (added to registry)
# ─────────────────────────────────────────────

def get_owner_commands():
    """Additional ownership-related voice commands."""
    from ownership import get_owner_info, get_transfer_history

    return [
        {
            "triggers": [
                "who owns you", "who is your owner", "current owner",
                "who controls you", "whose astra are you",
                "show owner", "owner info"
            ],
            "handler":          lambda _: get_owner_info(),
            "description":      "Show current owner information",
            "response_prefix":  ""
        },
        {
            "triggers": [
                "transfer history", "ownership history",
                "who owned you before", "previous owner",
                "show transfer log"
            ],
            "handler":          lambda _: get_transfer_history(),
            "description":      "Show ownership transfer history",
            "response_prefix":  "Here is the ownership history."
        },
    ]
