"""集中导入所有模型，确保它们注册到 Base.metadata（Alembic autogenerate 需要）。"""

from app.models.chat import ChatSession, Message
from app.models.knowledge import KnowledgeChunk, KnowledgeDoc
from app.models.ops import AuditLog, Feedback, QuestionPool
from app.models.user import Order, OrderItem, Product, User

__all__ = [
    "AuditLog",
    "ChatSession",
    "Feedback",
    "KnowledgeChunk",
    "KnowledgeDoc",
    "Message",
    "Order",
    "OrderItem",
    "Product",
    "QuestionPool",
    "User",
]
