import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"

    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    datasource_url: str = os.getenv("DATASOURCE_URL", "")
    datasource_username: str = os.getenv("DATASOURCE_USERNAME", "")
    datasource_password: str = os.getenv("DATASOURCE_PASSWORD", "")
    returned_message_worker_count: int = int(
        os.getenv("RETURNED_MESSAGE_WORKER_COUNT", "2")
    )
    returned_message_execution_lease_seconds: float = float(
        os.getenv("RETURNED_MESSAGE_EXECUTION_LEASE_SECONDS", "900")
    )
    returned_message_recovery_poll_interval_seconds: float = float(
        os.getenv("RETURNED_MESSAGE_RECOVERY_POLL_INTERVAL_SECONDS", "5")
    )
    returned_message_callback_base_url: str = os.getenv(
        "RETURNED_MESSAGE_CALLBACK_BASE_URL",
        "",
    )
    returned_message_callback_timeout_seconds: float = float(
        os.getenv("RETURNED_MESSAGE_CALLBACK_TIMEOUT_SECONDS", "5")
    )
    returned_message_callback_poll_interval_seconds: float = float(
        os.getenv("RETURNED_MESSAGE_CALLBACK_POLL_INTERVAL_SECONDS", "1")
    )
    returned_message_callback_max_attempts: int = int(
        os.getenv("RETURNED_MESSAGE_CALLBACK_MAX_ATTEMPTS", "3")
    )

    @property
    def is_development(self) -> bool:
        return self.app_env.strip().lower() in {"dev", "development", "local"}


settings = Settings()
