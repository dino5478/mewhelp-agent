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

- [ ] P0 脚手架：环境编排 + 建表 + 种子数据
- [ ] P1 服务层：FastAPI 分层 + 订单接口 + SSE 骨架
- [ ] P2 检索层：混合检索 + RRF + 重排 + 评测
- [ ] P3 编排层：LangGraph 状态图（意图分流 + 工具调用）
- [ ] P4 稳健性：置信度闸门 + 转人工 + 上下文档 + 中断恢复
- [ ] P5 可观测：Langfuse + 链路可视化
- [ ] P6 数据飞轮：问题池 + 运营工作台
- [ ] P7 微调 + 前端 + 打磨

> 详细设计与里程碑见 `docs/`（规划中）。

## 本地开发

```powershell
# 待 P0 完成后补充：uv sync / docker compose up -d / uvicorn ...
```

## 说明

本项目为个人学习与实践项目，复刻自小林coding《MewHelp 智能客服项目》的公开架构思路，具体实现为独立设计。
配置中的密钥/密码仅供本地开发，生产环境请务必替换。
