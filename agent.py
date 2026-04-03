"""
agent.py — ReAct Agent Loop with Auto-Learning
After every response, Astra automatically saves the Q&A to memory.
Next time a similar question is asked, she recalls her own past answers.
"""

import re
from tools import TOOLS, TOOL_DESCRIPTIONS
from llm import call_llm
from rag import search_rag, learn_from_conversation

MAX_ITERATIONS = 5

SYSTEM_PROMPT = """You are Astra, a helpful local AI assistant owned by Sowmik.

You have access to these tools:
{tool_list}

You also have access to your own memory from past conversations.
Relevant memories from past conversations:
{memory_context}

For each step respond ONLY in this exact format:
THOUGHT: <your reasoning about what to do>
ACTION: <tool name from the list above>
INPUT: <input to pass to the tool>

When you have a final answer respond ONLY in this format:
THOUGHT: <your reasoning>
FINAL: <your complete answer to Sowmik>

Rules:
- Always check memory context first before searching the web.
- Use one of the exact tool names listed above.
- INPUT must be a plain string.
- For create_file, INPUT format is: filename, file content here
- Keep answers concise and conversational.
- Address Sowmik by name occasionally to feel personal.
"""


def agent_loop(query: str) -> str:
    """
    Run the ReAct reasoning loop for a user query.
    Auto-learns from the query+response after completion.
    Returns the final response string.
    """

    # ── Step 1: Check memory for relevant past knowledge ──
    past_memories = search_rag(query, top_k=3)
    memory_context = ""
    if past_memories:
        memory_context = "\n".join(f"- {m}" for m in past_memories)
        print(f"[Agent] Found {len(past_memories)} relevant memories")
    else:
        memory_context = "No relevant memories found yet."

    # ── Step 2: Build tool list for prompt ──
    tool_list = "\n".join(
        f"  - {name}: {desc}"
        for name, desc in TOOL_DESCRIPTIONS.items()
    )

    history = []

    for iteration in range(MAX_ITERATIONS):
        # Build prompt with memory context
        history_text = ""
        if history:
            history_text = "\nObservations so far:\n" + "\n".join(
                f"  [{i+1}] {obs}" for i, obs in enumerate(history)
            )

        prompt = SYSTEM_PROMPT.format(
            tool_list=tool_list,
            memory_context=memory_context
        ) + f"""
Sowmik's query: {query}
{history_text}

Step {iteration + 1}:"""

        response = call_llm(prompt)
        print(f"[Agent] Step {iteration + 1}:\n{response}\n")

        # ── Check for final answer ──
        final_match = re.search(r"FINAL:\s*(.+)", response, re.DOTALL)
        if final_match:
            final_answer = final_match.group(1).strip()

            # ── Auto-learn from this conversation ──
            learn_from_conversation(query, final_answer)

            return final_answer

        # ── Parse ACTION and INPUT ──
        action_match = re.search(r"ACTION:\s*(\S+)", response)
        input_match  = re.search(
            r"INPUT:\s*(.+?)(?=\nTHOUGHT|\nACTION|\nFINAL|\Z)",
            response, re.DOTALL
        )

        if not action_match or not input_match:
            # No structured format — treat as final answer
            learn_from_conversation(query, response.strip())
            return response.strip()

        tool_name  = action_match.group(1).strip()
        tool_input = input_match.group(1).strip()

        # ── Execute tool ──
        if tool_name not in TOOLS:
            obs = f"Error: unknown tool '{tool_name}'. Available: {list(TOOLS.keys())}"
        else:
            try:
                if tool_name == "create_file":
                    parts = tool_input.split(",", 1)
                    obs = TOOLS[tool_name](parts[0].strip(), parts[1].strip()) \
                          if len(parts) == 2 else "Error: need 'filename, content'"
                else:
                    obs = TOOLS[tool_name](tool_input)
            except Exception as e:
                obs = f"Error running {tool_name}: {e}"

        print(f"[Agent] Tool result: {obs}")
        history.append(f"{tool_name}({tool_input!r}) -> {obs}")

    # ── Exhausted iterations ──
    final = f"Here's what I found: {history[-1]}" if history else \
            "I wasn't able to complete that task."

    # Still learn from it
    learn_from_conversation(query, final)
    return final
