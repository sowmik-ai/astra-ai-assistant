"""
self_repair.py — Astra Self-Repair Engine
Astra automatically:
1. Detects errors and crashes in real time
2. Diagnoses the root cause using LLM
3. Attempts to fix the broken code
4. Validates the fix before applying
5. Restarts affected modules without full reboot
6. Rolls back if fix makes things worse
7. Keeps a repair log of all fixes applied
"""

import os
import sys
import re
import json
import shutil
import importlib
import traceback
from datetime import datetime
from llm import call_llm
from rag import add_to_memory

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
REPAIR_LOG_FILE  = "astra_repair_log.json"
BACKUP_DIR       = "astra_backups"
REPAIRABLE_FILES = [
    "agent.py", "tools.py", "rag.py", "llm.py",
    "listener.py", "voice_auth.py", "self_learn.py",
    "self_improve.py", "self_repair.py"
]
MAX_REPAIR_ATTEMPTS = 3

# Voice callback
_speak = None

def set_voice(speak_fn):
    global _speak
    _speak = speak_fn

def say(text: str):
    print(f"[SelfRepair] {text}")
    if _speak:
        _speak(text)


# ─────────────────────────────────────────────
# ERROR HANDLER DECORATOR
# Wrap any function to auto-repair on failure
# ─────────────────────────────────────────────

def auto_repair(func):
    """
    Decorator — wraps a function with self-repair capability.
    If the function raises an exception, Astra tries to fix it.

    Usage:
        @auto_repair
        def my_function():
            ...
    """
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_REPAIR_ATTEMPTS):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = {
                    "function":  func.__name__,
                    "error":     str(e),
                    "traceback": traceback.format_exc(),
                    "attempt":   attempt + 1
                }
                print(f"[SelfRepair] Error in {func.__name__}: {e}")

                if attempt == 0:
                    say(f"I encountered an error in {func.__name__}. "
                        f"Let me diagnose and repair this now.")

                # Try to repair
                repaired = diagnose_and_repair(error_info)

                if not repaired and attempt == MAX_REPAIR_ATTEMPTS - 1:
                    say(f"I was unable to repair {func.__name__} after "
                        f"{MAX_REPAIR_ATTEMPTS} attempts. "
                        f"Falling back to safe mode.")
                    return _safe_fallback(func.__name__, str(e))

        return None
    return wrapper


# ─────────────────────────────────────────────
# CORE REPAIR ENGINE
# ─────────────────────────────────────────────

def diagnose_and_repair(error_info: dict) -> bool:
    """
    Main repair pipeline:
    1. Identify which file caused the error
    2. Back up the file
    3. Ask LLM to generate a fix
    4. Validate the fix
    5. Apply it
    6. Reload the module
    """
    error_msg  = error_info.get("error", "")
    tb         = error_info.get("traceback", "")
    func_name  = error_info.get("function", "unknown")

    say("Diagnosing the error now.")

    # ── Step 1: Identify broken file ──
    broken_file = _identify_broken_file(tb)
    if not broken_file:
        say("I could not identify which file caused the error. "
            "Logging for manual review.")
        _log_repair(error_info, "unidentified", False)
        return False

    say(f"The error is in {broken_file}. Let me read the file and generate a fix.")

    # ── Step 2: Read the broken file ──
    if not os.path.exists(broken_file):
        say(f"File {broken_file} not found. Cannot repair.")
        return False

    with open(broken_file, "r") as f:
        original_code = f.read()

    # ── Step 3: Back up the file ──
    backup_path = _backup_file(broken_file)
    say(f"Backup created at {backup_path}. Generating fix now.")

    # ── Step 4: Ask LLM to generate fix ──
    fix_prompt = f"""
You are an expert Python developer fixing a bug in Astra AI assistant.

Broken file: {broken_file}
Error message: {error_msg}
Traceback:
{tb}

Current code:
{original_code[:3000]}

Generate the COMPLETE fixed Python file.
Rules:
- Fix ONLY the specific error
- Do not change working functionality
- Keep all existing functions intact
- Add error handling where missing
- Return the COMPLETE file content, not just the fix

Return ONLY the raw Python code. No markdown, no explanation.
"""
    say("Asking my language model to generate a fix.")
    fixed_code = call_llm(fix_prompt, max_tokens=2000)

    # ── Step 5: Validate the fix ──
    say("Validating the generated fix.")
    valid, validation_msg = _validate_fix(fixed_code, broken_file)

    if not valid:
        say(f"Fix validation failed: {validation_msg}. "
            f"Restoring backup.")
        _restore_backup(backup_path, broken_file)
        _log_repair(error_info, broken_file, False, validation_msg)
        return False

    # ── Step 6: Apply the fix ──
    say(f"Validation passed. Applying fix to {broken_file}.")
    with open(broken_file, "w") as f:
        f.write(fixed_code)

    # ── Step 7: Reload the module ──
    reloaded = _reload_module(broken_file)

    if reloaded:
        say(f"Repair successful! {broken_file} has been fixed and reloaded. "
            f"I am fully operational again.")
        _log_repair(error_info, broken_file, True)
        add_to_memory(
            f"SELF-REPAIR: Fixed error in {broken_file}: {error_msg[:100]}",
            metadata={"type": "self_repair", "file": broken_file}
        )
        return True
    else:
        say(f"Module reload failed. Restoring backup.")
        _restore_backup(backup_path, broken_file)
        _log_repair(error_info, broken_file, False, "module reload failed")
        return False


# ─────────────────────────────────────────────
# PROACTIVE HEALTH CHECK
# Astra checks herself periodically
# ─────────────────────────────────────────────

def run_health_check() -> dict:
    """
    Proactively check all Astra modules for syntax errors,
    missing functions, and import issues.
    Returns health report.
    """
    say("Running full system health check.")

    report = {
        "timestamp": datetime.now().isoformat(),
        "healthy":   [],
        "warnings":  [],
        "errors":    []
    }

    for filename in REPAIRABLE_FILES:
        if not os.path.exists(filename):
            report["warnings"].append(f"{filename}: file not found")
            continue

        # Syntax check
        with open(filename, "r") as f:
            code = f.read()

        try:
            compile(code, filename, "exec")
            report["healthy"].append(filename)
        except SyntaxError as e:
            msg = f"{filename}: syntax error at line {e.lineno} — {e.msg}"
            report["errors"].append(msg)
            say(f"Syntax error detected in {filename}. Attempting repair.")
            diagnose_and_repair({
                "function":  filename,
                "error":     str(e),
                "traceback": f"SyntaxError in {filename} line {e.lineno}: {e.msg}"
            })

    healthy_count  = len(report["healthy"])
    error_count    = len(report["errors"])
    warning_count  = len(report["warnings"])

    summary = (
        f"Health check complete. "
        f"{healthy_count} modules healthy, "
        f"{error_count} errors found, "
        f"{warning_count} warnings."
    )

    if error_count == 0:
        say(f"All systems healthy. {healthy_count} modules operational.")
    else:
        say(f"Found {error_count} errors. Repair attempts completed.")

    return report


# ─────────────────────────────────────────────
# DEPENDENCY REPAIR
# Reinstall missing packages automatically
# ─────────────────────────────────────────────

def repair_missing_dependency(module_name: str) -> bool:
    """
    If a module import fails, try to install it automatically.
    """
    say(f"Missing dependency detected: {module_name}. "
        f"Attempting automatic installation.")

    # Map common import names to pip package names
    pip_names = {
        "speech_recognition": "SpeechRecognition",
        "faster_whisper":     "faster-whisper",
        "sounddevice":        "sounddevice",
        "resemblyzer":        "resemblyzer",
        "chromadb":           "chromadb",
        "pvporcupine":        "pvporcupine",
        "duckduckgo_search":  "duckduckgo-search",
        "sentence_transformers": "sentence-transformers",
        "pyttsx3":            "pyttsx3",
        "pyaudio":            "pyaudio",
    }

    pip_package = pip_names.get(module_name, module_name)

    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pip_package],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode == 0:
            say(f"Successfully installed {pip_package}. "
                f"Reloading now.")
            return True
        else:
            say(f"Failed to install {pip_package}. "
                f"Please install manually: pip install {pip_package}")
            return False

    except Exception as e:
        say(f"Auto-install failed: {e}")
        return False


# ─────────────────────────────────────────────
# ROLLBACK SYSTEM
# Restore from backup if something goes wrong
# ─────────────────────────────────────────────

def rollback_file(filename: str) -> bool:
    """Restore a file from its most recent backup."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backups = sorted([
        f for f in os.listdir(BACKUP_DIR)
        if f.startswith(filename.replace(".py", ""))
    ])

    if not backups:
        say(f"No backup found for {filename}.")
        return False

    latest_backup = os.path.join(BACKUP_DIR, backups[-1])
    shutil.copy2(latest_backup, filename)
    say(f"Rolled back {filename} to previous version from {backups[-1]}.")

    _reload_module(filename)
    return True


def list_backups() -> str:
    """List all available backups."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backups = os.listdir(BACKUP_DIR)
    if not backups:
        return "No backups available yet."
    return f"Available backups ({len(backups)}):\n" + \
           "\n".join(f"  - {b}" for b in sorted(backups)[-10:])


# ─────────────────────────────────────────────
# REPAIR LOG
# ─────────────────────────────────────────────

def get_repair_history() -> str:
    """Return summary of all self-repairs performed."""
    log = _load_repair_log()
    if not log:
        return "No self-repairs have been performed yet."

    successful = [r for r in log if r.get("success")]
    failed     = [r for r in log if not r.get("success")]

    return (
        f"I have performed {len(log)} repair attempts total. "
        f"{len(successful)} successful, {len(failed)} failed. "
        f"Most recent: {log[-1].get('file', 'unknown')} on "
        f"{log[-1].get('timestamp', 'unknown')[:10]}."
    )


# ─────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────

def _identify_broken_file(traceback_str: str) -> str:
    """Extract the most likely broken file from traceback."""
    for filename in REPAIRABLE_FILES:
        if filename in traceback_str:
            return filename
    # Try to find any .py file in traceback
    match = re.search(r'File "([^"]+\.py)"', traceback_str)
    if match:
        path = match.group(1)
        basename = os.path.basename(path)
        if basename in REPAIRABLE_FILES:
            return basename
    return None


def _backup_file(filename: str) -> str:
    """Create a timestamped backup of a file."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{filename.replace('.py', '')}_{timestamp}.py.bak"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    shutil.copy2(filename, backup_path)
    return backup_path


def _restore_backup(backup_path: str, original_file: str):
    """Restore a file from backup."""
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, original_file)
        print(f"[SelfRepair] Restored {original_file} from {backup_path}")


def _validate_fix(code: str, filename: str) -> tuple:
    """Validate generated code before applying."""
    # Check 1: Not empty
    if len(code.strip()) < 50:
        return False, "Generated code too short"

    # Check 2: Syntax check
    try:
        compile(code, filename, "exec")
    except SyntaxError as e:
        return False, f"Syntax error in fix: {e}"

    # Check 3: Safety check
    dangerous = ["os.system(", "shutil.rmtree", "os.remove(",
                 "subprocess.call", "eval(input", "exec(input"]
    for pattern in dangerous:
        if pattern in code:
            return False, f"Unsafe pattern detected: {pattern}"

    # Check 4: Key functions still present
    key_functions = {
        "agent.py":       ["agent_loop"],
        "tools.py":       ["web_search", "TOOLS"],
        "rag.py":         ["search_rag", "add_to_memory"],
        "llm.py":         ["call_llm"],
        "listener.py":    ["listen_audio"],
        "voice_auth.py":  ["is_my_voice"],
    }
    required = key_functions.get(filename, [])
    for func in required:
        if func not in code:
            return False, f"Key function '{func}' missing from fix"

    return True, "OK"


def _reload_module(filename: str) -> bool:
    """Reload a Python module after repair."""
    module_name = filename.replace(".py", "")
    try:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
            print(f"[SelfRepair] Reloaded module: {module_name}")
        return True
    except Exception as e:
        print(f"[SelfRepair] Reload failed for {module_name}: {e}")
        return False


def _safe_fallback(func_name: str, error: str) -> str:
    """Return a safe fallback response when repair fails."""
    return (
        f"I encountered an error in {func_name} that I could not repair. "
        f"Please check the repair log and restart Astra if needed."
    )


def _log_repair(error_info: dict, filename: str,
                success: bool, note: str = ""):
    """Log all repair attempts."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "file":      filename,
        "error":     error_info.get("error", "")[:200],
        "success":   success,
        "note":      note
    }
    log = _load_repair_log()
    log.append(entry)
    with open(REPAIR_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def _load_repair_log() -> list:
    if os.path.exists(REPAIR_LOG_FILE):
        with open(REPAIR_LOG_FILE, "r") as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    print("Running health check...")
    report = run_health_check()
    print(f"Healthy: {report['healthy']}")
    print(f"Errors:  {report['errors']}")
    print(f"Warnings:{report['warnings']}")
