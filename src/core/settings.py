from enum import StrEnum
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def to_logging_level(self) -> int:
        import logging

        mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }
        return mapping[self]


class Settings(BaseSettings):
    """应用配置。

    默认从环境变量和 .env 文件读取。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MODE: str | None = None

    HOST: str = "0.0.0.0"
    PORT: int = 8080
    LOG_LEVEL: LogLevel = LogLevel.INFO

    AUTH_SECRET: SecretStr | None = None
    OPENAI_API_KEY: SecretStr | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEEPSEEK_API_KEY: SecretStr | None = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    GEMAI_API_KEY: SecretStr | None = None
    GEMAI_BASE_URL: str = "https://api.gemai.cc/v1"
    GEMAI_RERANKER_MODEL: str = "qwen3-reranker-8b"
    
    # 核心组件开关：True 代表使用本地 BGE-M3， False 代表使用在线的 GEMAI Embedding
    USE_LOCAL_EMBEDDING: bool = False
    
    SILICONFLOW_PRIMARY_KEY: SecretStr | None = None
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_FALLBACK_KEY: SecretStr | None = None
    LANGFUSE_ENABLED: bool = True

    # PostgreSQL 关系与向量数据库配置
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "agentops"
    POSTGRES_USER: str = "agentops"
    POSTGRES_PASSWORD: str = "agentops_dev_password"

    @property
    def postgres_uri(self) -> str:
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis 配置 (用于并发锁控制)
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None

    @property
    def redis_uri(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # 默认模型设置
    DEFAULT_MODEL: str = "siliconflow/deepseek-ai/DeepSeek-V3.2"
    def is_dev(self) -> bool:
        return self.MODE == "dev"


settings = Settings()