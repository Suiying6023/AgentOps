from enum import StrEnum
from schema import ModelName, OpenAIModelName, SiliconFlowModelName
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
    DEEPSEEK_API_KEY: SecretStr | None = None
    
    SILICONFLOW_PRIMARY_KEY: SecretStr
    SILICONFLOW_FALLBACK_KEY: SecretStr
    LANGFUSE_ENABLED: bool = True

    # 默认模型设置 (更新为 DeepSeek-V3.2)
    DEFAULT_MODEL: ModelName = SiliconFlowModelName.DEEPSEEK_V3_2
    def is_dev(self) -> bool:
        return self.MODE == "dev"


settings = Settings()