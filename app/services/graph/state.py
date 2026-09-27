"""图状态：各节点共享的一张数据表。"""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict, total=False):
    # add_messages 让消息按追加方式合并，而不是覆盖
    messages: Annotated[list[BaseMessage], add_messages]
    query: str                 # 用户原始输入
    history: list[dict]        # 最近几轮对话，指代消解用
    user_id: int
    session_id: int
    standalone_query: str      # 补全后的独立问题
    intent: str
    route: str                 # faq / order / aftersale / agent
    context: str               # RAG 检索拼出的参考资料
    answer: str
