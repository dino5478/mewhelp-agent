"""应用配置：从 .env / 环境变量读取，统一用 settings 访问。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ===== 应用 =====
    APP_NAME: str = "mewhelp-agent"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = True

    # ===== 数据库 =====
    DATABASE_URL: str = (
        "mysql+pymysql://mewhelp:mewhelp_pass@127.0.0.1:3308/mewhelp_dev?charset=utf8mb4"
    )

    # ===== Redis =====
    REDIS_URL: str = "redis://127.0.0.1:6380/0"

    # ===== 认证 =====
    SECRET_KEY: str = "please-generate-a-random-secret-at-least-32-bytes"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ===== 大模型 =====
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TIMEOUT: int = 60

    # ===== 嵌入 / 重排 =====
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_TIMEOUT: int = 30
    EMBEDDING_DIM: int = 1024
    RERANK_BASE_URL: str = "https://api.siliconflow.cn/v1"
    RERANK_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANK_API_KEY: str = ""  # 留空则复用 EMBEDDING_API_KEY

    # ===== Milvus =====
    MILVUS_HOST: str = "127.0.0.1"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "mewhelp_kb"

    # ===== RAG 行为参数 =====
    RAG_TOP_K: int = 5
    RAG_RECALL_TOP_N: int = 20
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 80
    # ===== 置信度闸门：重排分高于阈值直接放行，低于则交给 LLM 自评 =====
    CONFIDENCE_SCORE_THRESHOLD: float = 0.3
    CONFIDENCE_SELF_EVAL: bool = True

    # ===== 可观测（Langfuse 云版；不填 key 则自动关闭）=====
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"


settings = Settings()
