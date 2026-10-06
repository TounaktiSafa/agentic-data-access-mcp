import argparse
import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import tracing  # noqa: E402
from src.agent.graph import build_graph  # noqa: E402
from src.agent.mcp_client import Warehouse  # noqa: E402
from src.agent.run import ask  # noqa: E402


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("--no-semantic", action="store_true")
    a = p.parse_args()
    async with Warehouse() as wh:
        graph = build_graph(wh, use_semantic=not a.no_semantic)
        out = await ask(graph, a.question, use_semantic=not a.no_semantic)
    print("SQL     :", out.get("sql"))
    print("ERROR   :", out.get("error") or "-")
    print("ANSWER  :", out["answer"])
    print(f"STATS   : {out['latency_s']:.1f}s | tokens in/out {out['tokens_in']}/{out['tokens_out']} "
          f"| attempts {out['attempts']}")
    tracing.flush()


asyncio.run(main())
