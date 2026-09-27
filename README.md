# MewHelp Agent — 电商 AI 智能客服

> 一个可上线的电商场景 AI 智能客服系统：意图识别 + RAG 混合检索 + Workflow/Agent 混合编排 + 置信度兜底 + 数据飞轮。

> A production-oriented e-commerce AI customer service agent built with Python, LangGraph, Milvus and FastAPI.

## 项目简介

MewHelp 是一条「用户消息进 → 回答出」的消息流水线：

```
用户问题 → 指代消解 + 意图识别 → 按意图分流(9类→5出口)
        → 子流程 / 主力 Agent(工具调用) → 置信度闸门
        → SSE 流式回答 → 留痕进问题池(数据飞轮)
```

核心设计：**确定的事交给 Workflow，需要判断的事交给 Agent。**

## 技术栈

| 分类 | 选型 |
|------|------|
| 语言 / 依赖 | Python 3.12+ / uv |
| Web | FastAPI + Uvicorn + SSE |
| 大模型 | DeepSeek（OpenAI 兼容） |
| 嵌入 / 重排 | BGE-M3 / BGE-Reranker-v2-m3 |
| 向量库 | Milvus（稠密 + BM25 稀疏） |
| 编排 | LangGraph |
| 数据库 | MySQL 8 + Redis 7 |
| 可观测 | Langfuse（规划中） |
| 微调 | RoBERTa-wwm-ext 意图分类器（规划中） |

## 功能进展

- [x] P0 脚手架：环境编排 + 建表 + 种子数据
- [ ] P1 服务层：FastAPI 分层 + 订单接口 + SSE 骨架
- [ ] P2 检索层：混合检索 + RRF + 重排 + 评测
- [ ] P3 编排层：LangGraph 状态图（意图分流 + 工具调用）
- [ ] P4 稳健性：置信度闸门 + 转人工 + 上下文档 + 中断恢复
- [ ] P5 可观测：Langfuse + 链路可视化
- [ ] P6 数据飞轮：问题池 + 运营工作台
- [ ] P7 微调 + 前端 + 打磨

> 详细设计与里程碑见 `docs/`（规划中）。

## 本地开发

前置：Docker Desktop、[uv](https://docs.astral.sh/uv/)（`pip install uv`）。

```powershell
# 1. 起基础设施（MySQL 3308 / Redis 6380；Milvus 栈 P2 再起）
docker compose up -d mysql redis

# 2. 装依赖（自动创建 .venv，使用 Python 3.12）
uv sync

# 3. 配置环境变量（填入模型 / 嵌入的 Key）
copy .env.example .env

# 4. 建表 + 灌种子数据
uv run alembic upgrade head
uv run python scripts/seed_data.py

# 5. 启动服务
uv run uvicorn app.main:app --reload
```

打开接口文档：http://127.0.0.1:8000/docs ，健康检查：http://127.0.0.1:8000/health

> 说明：`.env` 含密钥，已被 `.gitignore` 忽略，**不要提交**。

## 目录结构

```
app/
├── main.py            # FastAPI 入口（当前仅 /health）
├── database.py        # 引擎 + 会话 + Base + get_db
├── core/config.py     # 配置（pydantic-settings，读 .env）
└── models/            # ORM 模型（用户/商品/订单/知识/会话/问题池/反馈/审计）
migrations/            # Alembic 迁移
scripts/seed_data.py   # 种子数据
data/knowledge/        # 示例知识库文档（配送/退换货/支付）
tests/                 # pytest
docker-compose.yml     # MySQL + Redis + Milvus 栈
```

## 说明

本项目为个人学习与实践项目，复刻自小林coding《MewHelp 智能客服项目》的公开架构思路，具体实现为独立设计。
配置中的密钥/密码仅供本地开发，生产环境请务必替换。
