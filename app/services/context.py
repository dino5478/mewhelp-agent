"""双层上下文：近期对话保原文，更早的压缩成滚动摘要。

目的是长对话不丢早期信息，又不让 token 无限膨胀。
"""

from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from app.models import ChatSession, Message
from app.services import llm

RECENT_KEEP = 6        # 最近保留几轮原文
SUMMARIZE_AFTER = 12   # 消息数超过这个就触发摘要

_SUMMARY_PROMPT = """把下面的客服对话压缩成简短摘要，保留关键事实：涉及的单号、金额、诉求、\
已经给的结论。能一句话说清就别啰嗦。

已有摘要：{prev}

新增对话：
{text}

只输出摘要正文。"""


def _role_name(role: str) -> str:
    return "用户" if role == "user" else "客服"


def summarize_if_needed(db: Session, session: ChatSession) -> str | None:
    """消息太多时，把较早的部分汇总进 session.summary（原地更新，不删原始消息）。"""
    rows = (
        db.query(Message)
        .filter(Message.session_id == session.id)
        .order_by(Message.id)
        .all()
    )
    if len(rows) <= SUMMARIZE_AFTER:
        return session.summary

    older = rows[:-RECENT_KEEP]
    if not older:
        return session.summary

    text = "\n".join(f"{_role_name(m.role)}: {m.content}" for m in older)
    summary = llm.chat([
        HumanMessage(content=_SUMMARY_PROMPT.format(prev=session.summary or "（无）", text=text))
    ])
    session.summary = summary
    db.commit()
    db.refresh(session)
    return summary


def get_context(db: Session, session: ChatSession) -> dict:
    """返回 {summary 摘要, recent 最近几轮原文} 供指代消解/上下文使用。"""
    rows = (
        db.query(Message)
        .filter(Message.session_id == session.id, Message.role.in_(["user", "assistant"]))
        .order_by(Message.id.desc())
        .limit(RECENT_KEEP)
        .all()
    )
    recent = [{"role": m.role, "content": m.content} for m in reversed(rows)]
    return {"summary": session.summary or "", "recent": recent}
