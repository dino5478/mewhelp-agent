"""Agent 可调用的工具集。

用工厂方式按 user_id 建工具：订单类工具内部校验归属，别人的订单查不了。
工具出错时返回一句提示而不是抛异常，这样 Agent 能顺势回一句"没查到"。
"""

from langchain_core.tools import tool

from app.core.exceptions import AppException
from app.database import SessionLocal
from app.services import order_service, retrieval


def build_tools(user_id: int) -> list:
    @tool
    def search_knowledge_base(query: str) -> str:
        """查询知识库，回答运费、退换货、支付、发票、保修等规则类问题。"""
        chunks = retrieval.hybrid_search(query)
        if not chunks:
            return "知识库里没有找到相关内容。"
        # 带上标题路径，方便模型知道这条规则出自哪一节
        return "\n\n".join(f"[{c.heading_path}] {c.text}" for c in chunks)

    @tool
    def get_order(order_id: int) -> str:
        """按订单号查订单详情（状态、金额、商品）。"""
        db = SessionLocal()
        try:
            order = order_service.get_order(db, user_id, order_id)
            # 懒加载的关联要在会话关闭前取出来，否则会 DetachedInstanceError
            items = "、".join(
                f"{item.product_title or '商品'}x{item.quantity}" for item in order.items
            )
            return (
                f"订单 {order.id}：状态 {order.status}，"
                f"金额 {order.total_amount} 元，商品：{items or '无'}"
            )
        except AppException as exc:
            return f"查询订单失败：{exc.message}"
        finally:
            db.close()

    @tool
    def get_logistics(order_id: int) -> str:
        """按订单号查物流状态。"""
        db = SessionLocal()
        try:
            order = order_service.get_order(db, user_id, order_id)
            status = order.status
        except AppException as exc:
            return f"查询物流失败：{exc.message}"
        finally:
            db.close()

        if status in {"paid", "pending"}:
            return f"订单 {order_id} 还没发货，暂无可查的物流信息。"
        # 演示数据：真实项目这里会去调物流商接口
        return f"订单 {order_id} 已发货，运单号 SF{order_id:08d}，运输中。"

    return [search_knowledge_base, get_order, get_logistics]
