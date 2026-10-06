import time

from src import tracing


@tracing.observe(name="text_to_sql", capture_input=False, capture_output=False)
async def ask(graph, question: str, use_semantic: bool = True) -> dict:
    tracing.update_trace(
        name="text_to_sql",
        input=question,
        tags=["semantic" if use_semantic else "baseline"],
    )
    t0 = time.perf_counter()
    out = await graph.ainvoke({"question": question})
    out["latency_s"] = time.perf_counter() - t0
    tracing.update_trace(
        output={"sql": out.get("sql"), "answer": out.get("answer"), "error": out.get("error")},
        metadata={"attempts": out.get("attempts"), "tokens_in": out.get("tokens_in"),
                  "tokens_out": out.get("tokens_out")},
    )
    return out
