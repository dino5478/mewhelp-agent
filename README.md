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
- [x] P1 服务层：FastAPI 分层 + JWT 认证 + 订单接口 + SSE 骨架
- [x] P2 检索层：混合检索 + RRF + 重排 + 评测
- [x] P3 编排层：LangGraph 状态图（意图分流 + 工具调用）
- [x] P4 稳健性：置信度闸门 + 转人工 + 双层上下文 + 中断恢复
- [x] P5 可观测：Langfuse + 链路可视化
- [x] P6 数据飞轮：问题池 + 运营工作台
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

极简聊天页（验证 SSE 逐字效果）：http://127.0.0.1:8000/static/chat.html （默认账号 alice / alice123）

> 说明：`.env` 含密钥，已被 `.gitignore` 忽略，**不要提交**。

## 接口一览

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 否 |
| POST | `/users/register` | 注册 | 否 |
| POST | `/users/login` | 登录（表单），返回 JWT | 否 |
| GET | `/users/me` | 当前登录用户 | 是 |
| GET | `/orders` | 当前用户的订单列表 | 是 |
| GET | `/orders/{id}` | 订单详情（归属校验，非本人 403） | 是 |
| POST | `/chat/stream` | SSE 流式对话（意图分流 + RAG/Agent） | 是 |
| POST | `/chat/resume` | 中断后带选中的订单继续 | 是 |
| GET | `/trace/recent` | 最近的调用链概览 | 否 |
| GET | `/trace/{id}` | 某条调用链的节点耗时明细 | 否 |
| POST | `/feedback` | 点赞/点踩（点踩入问题池） | 是 |
| GET | `/ops/questions` | 问题池列表（按频次排序） | 否 |
| POST | `/ops/questions/{id}/approve` | 审核通过并回写知识库 | 否 |
| POST | `/ops/questions/{id}/reject` | 拒绝 | 否 |

### SSE 调用示例

```powershell
$token = (Invoke-RestMethod -Method Post "http://127.0.0.1:8000/users/login" `
  -Body @{username="alice"; password="alice123"}).access_token

curl.exe -N -X POST "http://127.0.0.1:8000/chat/stream" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $token" `
  -d "{\"message\": \"运费是多少？\"}"
```

## RAG 检索

流程：知识文档 → 按标题层级/表格切块 → 向量化(bge-m3) → 存 Milvus（稠密+BM25 稀疏）
→ 查询时双路召回 → RRF 融合 → bge-reranker 重排 → Top-K。

对照实验（`data/eval/retrieval_eval.jsonl`，28 条 query，7 篇知识文档 23 块）：

| 方案 | Recall@5 | Recall@10 | MRR |
|------|---------:|----------:|----:|
| dense_only | 1.000 | 1.000 | 0.946 |
| sparse_only | 0.964 | 0.964 | 0.876 |
| hybrid (RRF) | 1.000 | 1.000 | 0.940 |
| **hybrid + rerank** | **1.000** | **1.000** | **1.000** |

> 结论：仅 BM25 会漏召回；稠密/混合保证召回上限；**重排显著提升 MRR**（最相关块排到第一）。

复现：

```powershell
docker compose up -d                    # 起 MySQL/Redis/Milvus 栈
uv run python scripts/build_index.py    # 建库
uv run python scripts/eval_retrieval.py # 评测（需配置 EMBEDDING_API_KEY）
```

## 对话编排

一条消息的路径（LangGraph 状态图）：

```
用户消息
  → 指代消解 + 意图识别（9 类）
  → 分流：规则类走 RAG ｜ 订单/售后/闲聊走 Agent
  → RAG：混合检索 → 基于资料生成
  → Agent：ReAct 循环（可调 search_knowledge_base / get_order / get_logistics）
  → 逐 token SSE 返回
```

- 订单类工具**做归属校验**，只能查自己的订单。
- 意图出口映射：运费/商品/支付/发票 → RAG；订单/物流 → 订单工具；退换货/售后 → 售后工具；其它 → 通用 Agent。

命令行体验：

```powershell
uv run python scripts/chat_demo.py
```

## 稳健性

- **置信度闸门**：生成前先判证据够不够——重排分低于阈值时，再让 LLM 自评；不够就拒答/转人工，不硬编。
- **转人工**：答不准的问题连同检索快照写入 `question_pool`（数据飞轮入口），并给用户"已转人工"话术。
- **双层上下文**：近 6 轮保原文，更早的滚动压缩进 `chat_sessions.summary`，长对话不丢信息也不爆 token。
- **中断恢复**：售后流程若用户名下多笔订单，图会 `interrupt` 暂停并返回 `need_order_selection`；前端选单后调 `/chat/resume` 从断点继续。状态用 Redis checkpointer 持久化（需 redis-stack，带 RediSearch 模块）。

## 可观测

每次请求生成 `request_id`，按节点把耗时写进 `audit_logs`，本地即可查看调用链：

- 页面：`/static/trace.html`（也可直接调 `GET /trace/recent`、`GET /trace/{request_id}`）
- 云端：配置 `LANGFUSE_*` 后，会通过回调把 prompt/耗时/调用树上报 Langfuse（不配则自动降级为本地模式）

## 数据飞轮

答不准的问题不会白丢，三个入口沉淀进 `question_pool`（同问题按频次合并）：

- 检索证据弱被拒答、生成前自评未通过（转人工时自动记录）；
- 用户点踩（`POST /feedback`）。

运营在工作台按频次审核，**通过后把"问题+答案"作为新文档回写知识库**（切块+向量化+入 Milvus），下次用户就能问到。

- 工作台页面：`/static/ops.html`
- 接口：`GET /ops/questions`、`POST /ops/questions/{id}/approve`、`POST /ops/questions/{id}/reject`

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
