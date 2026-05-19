"""
intent.py — Flexible Keyword Command Router

RULE:
  - Each command has multiple keyword_sets (aliases/synonyms)
  - ANY one set fully matching = execute command
  - Some keywords from any set present = suggest
  - No keywords at all = agent handles normally (AI answers)

"agent loop" means llama3 answers your question normally —
searches web, uses tools, speaks the answer. NOT ignored.
"""

import re
from datetime import datetime

KEYWORD_COMMANDS = {

    # ── HEALTH & REPAIR ──────────────────────────────────────
    "health_check": {
        "keyword_sets": [
            ["health", "check"],
            ["system", "check"],
            ["system", "health"],
            ["run", "diagnostics"],
            ["check", "modules"],
            ["check", "status"],
            ["all", "systems"],
        ],
        "description": "Run full system health check on all modules",
        "example":     "astra do health check",
    },
    "repair_run": {
        "keyword_sets": [
            ["repair", "yourself"],
            ["fix", "yourself"],
            ["fix", "error"],
            ["repair", "error"],
            ["self", "repair"],
            ["fix", "bug"],
        ],
        "description": "Repair any broken modules",
        "example":     "astra repair yourself",
    },
    "repair_history": {
        "keyword_sets": [
            ["repair", "history"],
            ["repair", "log"],
            ["show", "repairs"],
            ["fixed", "before"],
        ],
        "description": "Show self-repair history",
        "example":     "astra show repair history",
    },
    "list_backups": {
        "keyword_sets": [
            ["list", "backups"],
            ["show", "backups"],
            ["available", "backups"],
            ["check", "backups"],
        ],
        "description": "List all available file backups",
        "example":     "astra list backups",
    },
    "rollback_file": {
        "keyword_sets": [
            ["rollback"],
            ["restore", "file"],
            ["revert", "file"],
        ],
        "description": "Rollback a file to previous version",
        "example":     "astra rollback tools.py",
    },

    # ── LEARNING & SKILLS ────────────────────────────────────
    "skill_library": {
        "keyword_sets": [
            ["skill", "library"],
            ["show", "skills"],
            ["list", "skills"],
            ["your", "skills"],
            ["new", "skills"],
            ["created", "tools"],
            ["what", "skills"],
        ],
        "description": "Show all skills Astra created autonomously",
        "example":     "astra show skill library",
    },
    "learning_stats": {
        "keyword_sets": [
            ["learning", "stats"],
            ["learning", "progress"],
            ["show", "progress"],
            ["improvement", "progress"],
            ["how", "improving"],
            ["getting", "smarter"],
            ["task", "history"],
        ],
        "description": "Show learning and improvement statistics",
        "example":     "astra show learning stats",
    },
    "task_patterns": {
        "keyword_sets": [
            ["task", "patterns"],
            ["performance", "analysis"],
            ["good", "at"],
            ["struggle", "with"],
            ["best", "tasks"],
        ],
        "description": "Analyse what task types Astra performs best",
        "example":     "astra analyze task patterns",
    },
    "self_reflect": {
        "keyword_sets": [
            ["improve", "yourself"],
            ["self", "reflect"],
            ["self", "improvement"],
            ["review", "mistakes"],
            ["learn", "mistakes"],
            ["analyze", "performance"],
        ],
        "description": "Astra reflects on mistakes and improves",
        "example":     "astra improve yourself",
    },
    "improvement_stats": {
        "keyword_sets": [
            ["improvement", "stats"],
            ["feedback", "stats"],
            ["rating", "history"],
            ["how", "rated"],
        ],
        "description": "Show feedback and rating statistics",
        "example":     "astra show improvement stats",
    },

    # ── MEMORY ───────────────────────────────────────────────
    "memory_count": {
        "keyword_sets": [
            ["memory", "count"],
            ["how", "memories"],
            ["memory", "size"],
            ["total", "memories"],
        ],
        "description": "Show how many memories Astra has",
        "example":     "astra memory count",
    },
    "show_memories": {
        "keyword_sets": [
            ["show", "memories"],
            ["list", "memories"],
            ["recent", "memories"],
            ["your", "memories"],
        ],
        "description": "Show recent memories",
        "example":     "astra show memories",
    },
    "clear_learned": {
        "keyword_sets": [
            ["clear", "learned"],
            ["delete", "learned"],
            ["forget", "learned"],
            ["remove", "learned"],
        ],
        "description": "Clear auto-learned memories only",
        "example":     "astra clear learned memories",
    },
    "clear_memory": {
        "keyword_sets": [
            ["clear", "memory"],
            ["delete", "memory"],
            ["wipe", "memory"],
            ["reset", "memory"],
            ["forget", "everything"],
        ],
        "description": "Clear all memories (asks confirmation)",
        "example":     "astra clear memory",
    },

    # ── REMINDERS ────────────────────────────────────────────
    "set_reminder": {
        "keyword_sets": [
            ["remind"],
            ["set", "reminder"],
            ["add", "reminder"],
            ["new", "reminder"],
            ["wake", "me"],
            ["alert", "me"],
            ["notify", "me"],
        ],
        "description": "Set a reminder — include time and message",
        "example":     "astra remind me at 3pm to call John",
    },
    "set_alarm": {
        "keyword_sets": [
            ["set", "alarm"],
            ["alarm", "for"],
            ["add", "alarm"],
        ],
        "description": "Set an alarm",
        "example":     "astra set alarm for 7am",
    },
    "list_reminders": {
        "keyword_sets": [
            ["list", "reminders"],
            ["show", "reminders"],
            ["my", "reminders"],
            ["upcoming", "reminders"],
            ["any", "reminders"],
            ["what", "reminders"],
            ["what", "scheduled"],
            ["anything", "scheduled"],
        ],
        "description": "List all pending reminders",
        "example":     "astra list reminders",
    },
    "cancel_reminder": {
        "keyword_sets": [
            ["cancel", "reminder"],
            ["delete", "reminder"],
            ["remove", "reminder"],
            ["cancel", "alarm"],
        ],
        "description": "Cancel a specific reminder",
        "example":     "astra cancel reminder call John",
    },
    "clear_reminders": {
        "keyword_sets": [
            ["clear", "reminders"],
            ["delete", "all", "reminders"],
            ["remove", "all", "reminders"],
            ["clear", "all", "reminders"],
        ],
        "description": "Clear all reminders",
        "example":     "astra clear all reminders",
    },

    # ── SYSTEM ───────────────────────────────────────────────
    "check_ollama": {
        "keyword_sets": [
            ["check", "ollama"],
            ["ollama", "running"],
            ["check", "llm"],
            ["llm", "status"],
            ["brain", "working"],
            ["model", "running"],
        ],
        "description": "Check if Ollama LLM is running",
        "example":     "astra check ollama",
    },
    "list_models": {
        "keyword_sets": [
            ["list", "models"],
            ["show", "models"],
            ["available", "models"],
            ["which", "models"],
        ],
        "description": "List available Ollama AI models",
        "example":     "astra list models",
    },
    "get_time": {
        "keyword_sets": [
            ["current", "time"],
            ["what", "time"],
            ["today", "date"],
            ["current", "date"],
            ["what", "day"],
        ],
        "description": "Get current date and time",
        "example":     "astra what time is it",
    },
    "show_help": {
        "keyword_sets": [
            ["show", "commands"],
            ["list", "commands"],
            ["all", "commands"],
            ["available", "commands"],
            ["help", "commands"],
        ],
        "description": "Show all available voice commands",
        "example":     "astra show commands",
    },
    "end_session": {
        "keyword_sets": [
            ["end", "session"],
            ["close", "session"],
            ["finish", "session"],
        ],
        "description": "End current session and lock Astra",
        "example":     "astra end session",
    },
    "lock_astra": {
        "keyword_sets": [
            ["lock"],
            ["log", "out"],
            ["sign", "out"],
            ["logout"],
        ],
        "description": "Lock Astra",
        "example":     "astra lock",
    },
    "stop_astra": {
        "keyword_sets": [
            ["stop"],
            ["shutdown"],
            ["turn", "off"],
            ["goodbye"],
            ["bye"],
        ],
        "description": "Stop Astra",
        "example":     "astra stop",
    },

    # ── OWNERSHIP ────────────────────────────────────────────
    "owner_info": {
        "keyword_sets": [
            ["owner", "info"],
            ["who", "owns"],
            ["current", "owner"],
            ["show", "owner"],
        ],
        "description": "Show current owner information",
        "example":     "astra owner info",
    },
    "transfer_history": {
        "keyword_sets": [
            ["transfer", "history"],
            ["ownership", "history"],
            ["previous", "owner"],
            ["past", "owners"],
        ],
        "description": "Show ownership transfer history",
        "example":     "astra transfer history",
    },

    # ── AUTH / SECURITY ──────────────────────────────────────
    "auth_status": {
        "keyword_sets": [
            ["auth", "status"],
            ["security", "status"],
            ["mfa", "status"],
            ["check", "auth"],
            ["check", "security"],
            ["authentication", "status"],
        ],
        "description": "Show MFA authentication status",
        "example":     "astra auth status",
    },
    "auth_log": {
        "keyword_sets": [
            ["auth", "log"],
            ["login", "history"],
            ["access", "log"],
            ["security", "log"],
            ["who", "accessed"],
        ],
        "description": "Show recent authentication attempts",
        "example":     "astra auth log",
    },
    "set_pin": {
        "keyword_sets": [
            ["set", "pin"],
            ["change", "pin"],
            ["new", "pin"],
            ["update", "pin"],
        ],
        "description": "Set or change voice PIN",
        "example":     "astra set pin",
    },
    "set_passphrase": {
        "keyword_sets": [
            ["set", "passphrase"],
            ["change", "passphrase"],
            ["new", "passphrase"],
            ["secret", "phrase"],
        ],
        "description": "Set or change secret passphrase",
        "example":     "astra set passphrase",
    },
    "set_knock": {
        "keyword_sets": [
            ["set", "knock"],
            ["knock", "pattern"],
            ["change", "knock"],
            ["new", "knock"],
        ],
        "description": "Set knock authentication pattern",
        "example":     "astra set knock pattern",
    },
    "add_mfa_factor": {
        "keyword_sets": [
            ["add", "factor"],
            ["add", "mfa"],
            ["enable", "factor"],
            ["add", "authentication"],
        ],
        "description": "Add an MFA authentication factor",
        "example":     "astra add mfa factor",
    },
    "remove_mfa_factor": {
        "keyword_sets": [
            ["remove", "factor"],
            ["disable", "factor"],
            ["remove", "mfa"],
            ["disable", "mfa"],
        ],
        "description": "Remove an MFA authentication factor",
        "example":     "astra remove mfa factor",
    },

    # ── AWS / CLOUD ───────────────────────────────────────────
    "aws_alarms": {
        "keyword_sets": [
            ["check", "alarms"],
            ["aws", "alarms"],
            ["cloudwatch", "alarms"],
            ["show", "alarms"],
            ["list", "alarms"],
        ],
        "description": "Check CloudWatch alarms",
        "example":     "astra check alarms",
    },
    "aws_ec2": {
        "keyword_sets": [
            ["list", "ec2"],
            ["show", "ec2"],
            ["ec2", "instances"],
            ["running", "instances"],
            ["check", "ec2"],
        ],
        "description": "List EC2 instances",
        "example":     "astra list ec2 instances",
    },
    "aws_stacks": {
        "keyword_sets": [
            ["list", "stacks"],
            ["show", "stacks"],
            ["cloudformation", "stacks"],
            ["all", "stacks"],
        ],
        "description": "List CloudFormation stacks",
        "example":     "astra list stacks",
    },
    "aws_stack_status": {
        "keyword_sets": [
            ["stack", "status"],
            ["check", "stack"],
            ["stack", "health"],
        ],
        "description": "Check a specific CloudFormation stack",
        "example":     "astra stack status gpsi-asc-stack",
    },
    "aws_logs": {
        "keyword_sets": [
            ["query", "logs"],
            ["search", "logs"],
            ["cloudwatch", "logs"],
            ["check", "logs"],
        ],
        "description": "Query CloudWatch logs",
        "example":     "astra query logs /aws/lambda/my-fn ERROR",
    },
    "aws_cost": {
        "keyword_sets": [
            ["aws", "cost"],
            ["cloud", "cost"],
            ["aws", "bill"],
            ["aws", "spend"],
            ["how", "cost"],
        ],
        "description": "Get AWS cost estimate",
        "example":     "astra aws cost",
    },
    "aws_lambda": {
        "keyword_sets": [
            ["list", "lambda"],
            ["show", "lambda"],
            ["lambda", "functions"],
            ["check", "lambda"],
        ],
        "description": "List Lambda functions",
        "example":     "astra list lambda functions",
    },
    "gpsi_status": {
        "keyword_sets": [
            ["gpsi", "status"],
            ["check", "gpsi"],
            ["gpsi", "check"],
            ["asc", "status"],
            ["gpsi", "asc"],
        ],
        "description": "Check all GPSI-ASC stacks and alarms",
        "example":     "astra check gpsi status",
    },
}


# ─────────────────────────────────────────────
# MATCHING ENGINE
# ─────────────────────────────────────────────

def _has(word: str, text: str) -> bool:
    """Whole-word match."""
    return bool(re.search(r'\b' + re.escape(word) + r'\b', text))


def route(text: str) -> tuple:
    """
    Route spoken text to a command.

    Returns:
      (command_id, extras)      → ALL keywords of one set present → execute
      ("suggestion", extras)    → SOME keywords present → hint what's missing
      (None, {})                → NO keywords → agent answers normally

    NOTE: (None, {}) = agent loop = llama3 answers your question normally.
          It is NOT ignored. Astra speaks the full answer.
    """
    # Strip wake word so "astra" never counts as a keyword
    t = re.sub(r'\bastra\b', '', text.lower()).strip()

    full_matches    = []
    partial_matches = {}   # cid → best partial for that command

    for cid, cfg in KEYWORD_COMMANDS.items():
        for kset in cfg["keyword_sets"]:
            present = [kw for kw in kset if _has(kw, t)]
            missing = [kw for kw in kset if not _has(kw, t)]

            if not missing:
                # ALL keywords present → full match
                full_matches.append((cid, kset))
                break   # no need to check other sets for this command
            elif present:
                # SOME keywords → track best partial for this command
                ratio = len(present) / len(kset)
                if cid not in partial_matches or \
                   ratio > partial_matches[cid]["ratio"]:
                    partial_matches[cid] = {
                        "present": present,
                        "missing": missing,
                        "ratio":   ratio,
                        "example": cfg["example"],
                    }

    # ── Return full match (first one wins) ──
    if full_matches:
        cid, kset = full_matches[0]
        print(f"[Intent] EXECUTE: {cid} via {kset}")
        return cid, _extract_extras(text, cid)

    # ── Return suggestion for best partial match ──
    if partial_matches:
        best_cid = max(partial_matches,
                       key=lambda c: partial_matches[c]["ratio"])
        info      = partial_matches[best_cid]
        missing_w = info["missing"][0]
        present_w = " + ".join(info["present"])
        msg = (
            f"I heard '{present_w}' — "
            f"also say '{missing_w}' to run that command. "
            f"Try: '{info['example']}'"
        )
        # Show one more alternative if available
        others = [c for c in partial_matches if c != best_cid]
        if others:
            alt = partial_matches[others[0]]["example"]
            msg += f" — or: '{alt}'"
        print(f"[Intent] SUGGEST for {best_cid}")
        return "suggestion", {"message": msg}

    # ── No match → agent answers normally ──
    print(f"[Intent] AGENT: {text!r}")
    return None, {}


def _extract_extras(text: str, cid: str) -> dict:
    """Pull useful data from the sentence."""
    extras = {}
    t = text.lower()
    if cid == "rollback_file":
        m = re.search(r'\b(\w+\.py)\b', t)
        if m: extras["filename"] = m.group(1)
    if cid in ["set_reminder", "set_alarm"]:
        m = re.search(
            r'\b(\d{1,2}(?::\d{2})?\s*(?:am|pm)|'
            r'in \d+\s*(?:minutes?|hours?))\b', t)
        if m: extras["time"] = m.group(0)
    if cid == "aws_stack_status":
        m = re.search(r'(gpsi[\w-]+|[\w-]+-stack[\w-]*)', t)
        if m: extras["stack_name"] = m.group(1)
    return extras


# ─────────────────────────────────────────────
# EXECUTE COMMAND
# ─────────────────────────────────────────────

def execute(cid: str, text: str, extras: dict) -> str:
    """Execute matched command and return response string."""

    if cid == "health_check":
        from self_repair import run_health_check
        r = run_health_check()
        ok, er = len(r["healthy"]), len(r["errors"])
        return (f"All {ok} modules are healthy."
                if er == 0 else
                f"{ok} healthy, {er} errors found and repair attempted.")

    if cid == "repair_run":
        from self_repair import run_health_check, diagnose_and_repair
        r = run_health_check()
        if not r["errors"]: return "No errors found. All systems healthy."
        fixed = sum(1 for e in r["errors"] if diagnose_and_repair(
            {"function":"health_check","error":e,"traceback":e}))
        return f"Repaired {fixed} of {len(r['errors'])} errors."

    if cid == "repair_history":
        from self_repair import get_repair_history
        return get_repair_history()

    if cid == "list_backups":
        from self_repair import list_backups
        return list_backups()

    if cid == "rollback_file":
        from self_repair import rollback_file
        f = extras.get("filename","")
        if not f: return "Say the filename too. Example: astra rollback tools.py"
        return "Rollback successful." if rollback_file(f) else f"No backup for {f}."

    if cid == "skill_library":
        from self_learn import get_skill_library
        return get_skill_library()

    if cid == "learning_stats":
        from self_learn import get_learning_stats
        return get_learning_stats()

    if cid == "task_patterns":
        from self_learn import analyze_task_patterns
        return analyze_task_patterns()

    if cid == "self_reflect":
        from self_improve import analyze_performance
        return analyze_performance()

    if cid == "improvement_stats":
        from self_improve import get_improvement_stats
        return get_improvement_stats()

    if cid == "memory_count":
        from rag import get_memory_count
        return f"I have {get_memory_count()} memories stored."

    if cid == "show_memories":
        from rag import list_memories
        mems = list_memories(limit=5)
        if not mems: return "No memories yet."
        return "Recent memories:\n" + "\n".join(
            f"  {i+1}. {m['text'][:80]}" for i,m in enumerate(mems))

    if cid == "clear_learned":
        from rag import clear_learned_memories
        clear_learned_memories()
        return "Auto-learned memories cleared."

    if cid == "clear_memory":
        return "AWAITING_CONFIRMATION:clear_memory"

    if cid in ["set_reminder","set_alarm"]:
        from scheduler import add_reminder
        return add_reminder(text)

    if cid == "list_reminders":
        from scheduler import list_reminders
        return list_reminders()

    if cid == "cancel_reminder":
        from scheduler import cancel_reminder
        return cancel_reminder(text)

    if cid == "clear_reminders":
        from scheduler import clear_all_reminders
        return clear_all_reminders()

    if cid == "check_ollama":
        from llm import is_ollama_running
        return ("Ollama is running and ready."
                if is_ollama_running()
                else "Ollama not running. Run: ollama serve")

    if cid == "list_models":
        from llm import list_models
        m = list_models()
        return f"Available: {', '.join(m)}." if m else "No models found."

    if cid == "get_time":
        return datetime.now().strftime("It is %A, %d %B %Y at %H:%M.")

    if cid == "show_help":
        lines = ["Say 'astra' + keywords to run commands:\n"]
        for c, cfg in KEYWORD_COMMANDS.items():
            aliases = " | ".join(
                " + ".join(kset)
                for kset in cfg["keyword_sets"][:2]
            )
            lines.append(f"  [{aliases}]  →  {cfg['description']}")
        lines.append("\nAnything else → AI agent answers your question.")
        return "\n".join(lines)

    if cid in ["end_session","lock_astra","lock"]:
        from auth import end_session
        return end_session()

    if cid == "stop_astra":
        return "STOP_SIGNAL"

    if cid == "owner_info":
        from ownership import get_owner_info
        return get_owner_info()

    if cid == "transfer_history":
        from ownership import get_transfer_history
        return get_transfer_history()

    if cid == "auth_status":
        from auth import get_auth_status
        return get_auth_status()

    if cid == "auth_log":
        from auth import get_auth_log
        return get_auth_log()

    if cid == "set_pin":
        from auth import setup_voice_pin
        return setup_voice_pin()

    if cid == "set_passphrase":
        from auth import setup_voice_passphrase
        return setup_voice_passphrase()

    if cid == "set_knock":
        # knock pattern removed — voice-only MFA uses voice_passphrase
        from auth import setup_voice_passphrase
        return setup_voice_passphrase()

    if cid == "add_mfa_factor":
        from auth import add_factor
        t = text.lower()
        if "passphrase" in t or "phrase" in t:
            return add_factor("voice_passphrase")
        if "pin" in t:
            return add_factor("voice_pin")
        if "identity" in t or "biometric" in t:
            return add_factor("voice_identity")
        return ("Which factor? Say: voice pin, or voice passphrase.")

    if cid == "remove_mfa_factor":
        from auth import remove_factor
        t = text.lower()
        if "passphrase" in t or "phrase" in t:
            return remove_factor("voice_passphrase")
        if "pin" in t:
            return remove_factor("voice_pin")
        return ("Which factor to remove? Say: voice pin or voice passphrase.")

    if cid == "aws_alarms":
        from aws_tools import check_cloudwatch_alarms
        return check_cloudwatch_alarms()

    if cid == "aws_ec2":
        from aws_tools import list_ec2_instances
        return list_ec2_instances()

    if cid == "aws_stacks":
        from aws_tools import list_stacks
        return list_stacks()

    if cid == "aws_stack_status":
        from aws_tools import check_stack_status
        sn = extras.get("stack_name","")
        if not sn: return "Say the stack name too."
        return check_stack_status(sn)

    if cid == "aws_logs":
        from aws_tools import query_logs
        return query_logs(text)

    if cid == "aws_cost":
        from aws_tools import get_aws_cost
        return get_aws_cost()

    if cid == "aws_lambda":
        from aws_tools import list_lambda_functions
        return list_lambda_functions()

    if cid == "gpsi_status":
        from aws_tools import check_gpsi_asc_status
        return check_gpsi_asc_status()

    return f"Command '{cid}' matched but no handler found."
