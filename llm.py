"""
llm.py — LLM Interface (Ollama)
Sends prompts to a locally-running Ollama instance.
Supports streaming and non-streaming modes.
"""

import requests
import json

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3"          # Change to: mistral, phi3, llama3.1, etc.
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 512


# ─────────────────────────────────────────────
# NON-STREAMING (used by agent)
# ─────────────────────────────────────────────

def call_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    system: str = None
) -> str:
    """
    Send a prompt to Ollama and return the complete response text.

    Args:
        prompt:      The user prompt.
        model:       Ollama model name.
        temperature: Sampling temperature (0 = deterministic, 1 = creative).
        max_tokens:  Max tokens in the response.
        system:      Optional system prompt override.

    Returns:
        Response text string.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=120
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:
        return "[ERROR] Cannot connect to Ollama. Is 'ollama serve' running?"
    except requests.exceptions.Timeout:
        return "[ERROR] LLM request timed out."
    except Exception as e:
        return f"[ERROR] LLM call failed: {e}"


# ─────────────────────────────────────────────
# STREAMING (optional — for real-time output)
# ─────────────────────────────────────────────

def call_llm_stream(prompt: str, model: str = DEFAULT_MODEL):
    """
    Generator that yields response tokens one by one.
    Use for real-time display in a terminal or UI.

    Usage:
        for token in call_llm_stream("Hello"):
            print(token, end="", flush=True)
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True
    }
    try:
        with requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            stream=True,
            timeout=120
        ) as resp:
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
    except Exception as e:
        yield f"[ERROR] {e}"


# ─────────────────────────────────────────────
# MODEL MANAGEMENT HELPERS
# ─────────────────────────────────────────────

def list_models() -> list[str]:
    """Return a list of locally available Ollama models."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        models = resp.json().get("models", [])
        return [m["name"] for m in models]
    except Exception:
        return []


def is_ollama_running() -> bool:
    """Check if the Ollama server is reachable."""
    try:
        requests.get(OLLAMA_BASE_URL, timeout=3)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    if is_ollama_running():
        print("Ollama is running. Available models:", list_models())
        print(call_llm("Say hello in one sentence."))
    else:
        print("Ollama is NOT running. Start it with: ollama serve")
