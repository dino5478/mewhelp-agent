# 项目约定（AGENTS.md）

本文件记录 MewHelp 项目的开发约定，人和 AI 助手都按这个来。

## 项目一句话

电商 AI 智能客服：意图识别 + 混合检索 RAG + Workflow/Agent 混合编排 + 置信度兜底。

## 注释规范：写成人话

注释是给"三个月后的自己"看的，不是给机器看的。遵守下面几条：

- **只写为什么，不写是什么**。代码能看懂的别再复述一遍；注释用来交代背景、坑、取舍。
  - 反例：`# 把用户存进数据库`（废话）
  - 正例：`# 手机号要唯一，先查再插，避免并发下重复注册`
- **中文、短句、口语一点**，长短不齐没关系。简单的行不加注释，关键处多写两句。
- **别用 AI 腔**：不写"注意：""请确保""以下代码""这是一个…的示例""如上所述"，不堆 emoji，不写整齐排比。
- **分节注释按需**，不要每条都套一个一模一样的 banner，看着像自动生成的。
- **关键决策留一句背景**，比如"minio 官方镜像下架了，改用 SeaweedFS 顶替"——这种信息最值钱。

## 提交规范

- **小步骤提交**：完成一个可验证的小步骤（测试/冒烟过）就提交一次；验证不过先修，不留半成品提交。
- **信息用英文**，Conventional Commits：`feat:` / `fix:` / `refactor:` / `test:` / `docs:` / `chore:`，一个提交只干一件事。
- **阶段打 tag**：P0→`v0.1.0`，P1→`v0.2.0`……每个阶段（P）完成时打一个。
- **不伪造历史**，绝不 force push 改写已推送的记录。

## 写代码时

- 分层：`routers`（收请求）/ `services`（业务）/ `models`（存储）/ `schemas`（传输），别混。
- 外部依赖（大模型、向量库、Redis）尽量可 mock，保证测试能离线跑。
- 新增行为尽量补一条测试；测试要真的断言到点上，别只跑通就算过。

## 环境

- Python 3.12 + uv（`python -m uv ...`）
- 基础设施：`docker compose up -d`（MySQL 3308 / Redis 6380 / Milvus 19530）
- 常用命令：
  - 建库：`python -m uv run python scripts/build_index.py`
  - 评测：`python -m uv run python scripts/eval_retrieval.py`
  - 测试：`python -m uv run pytest`
  - 检查：`python -m uv run ruff check .`
