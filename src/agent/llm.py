import os

import ollama

from src import tracing

MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
_client = ollama.AsyncClient()


@tracing.observe(as_type="generation", name="llm.chat")
async def chat(system: str, user: str, json_mode: bool = False) -> tuple[str, int, int]:
    """Return (text, prompt_tokens, completion_tokens). Tokens feed the cost metric."""
    resp = await _client.chat(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        format="json" if json_mode else None,
        options={"temperature": 0},
    )
    text = resp["message"]["content"]
    tin = resp.get("prompt_eval_count", 0) or 0
    tout = resp.get("eval_count", 0) or 0
    tracing.update_generation(
        model=MODEL,
        input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        output=text,
        usage_details={"input": tin, "output": tout},
    )
    return text, tin, tout
