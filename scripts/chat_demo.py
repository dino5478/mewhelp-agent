"""命令行体验：跑几个问题，看意图、路由、工具调用和回答。

用法（项目根目录）:
    python -m uv run python scripts/chat_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.graph.build import build_graph


def run(user_id: int, query: str, history: list[dict] | None = None) -> None:
    graph = build_graph(user_id)
    state = graph.invoke(
        {"query": query, "user_id": user_id, "session_id": 0, "history": history or []}
    )
    print(f"\nQ: {query}")
    print(f"   意图={state.get('intent')}  路由={state.get('route')}")
    for msg in state.get("messages", []):
        for call in getattr(msg, "tool_calls", None) or []:
            print(f"   调用工具: {call['name']}({call['args']})")
    print(f"A: {state.get('answer')}")


if __name__ == "__main__":
    run(1, "运费是多少？")                       # 走 RAG
    run(1, "帮我查一下订单 1 的状态")            # 走工具
    run(1, "订单 999 现在什么情况")              # 工具查不到，优雅兜底
    # 依赖上文的半截话：指代消解会把"它"补成订单
    run(
        1,
        "那它能退吗",
        history=[
            {"role": "user", "content": "订单 1 是什么情况"},
            {"role": "assistant", "content": "订单 1 已发货。"},
        ],
    )
