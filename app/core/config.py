from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = "Enterprise IT Support Agentic RAG Copilot"
    app_env: str = "development"
    openai_api_key: str = ""
    tavily_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index_name: str = "fde-it-support-rag"
    pinecone_namespace: str = "company-it-kb"
    embedding_model: str = "text-embedding-3-small"
    openai_model: str = "gpt-4o-mini"
    top_k: int = 4
    max_retries: int = 1
    jwt_secret: str
    jwt_expire_minutes: int = 60
    cookie_secure: bool = False
    demo_email: str = ""
    chat_rate_per_ip: int = 15
    chat_rate_per_user: int = 300
    hr_db_path: str = str(BASE_DIR / "data" / "hr.db")
    app_db_path: str = str(BASE_DIR / "data" / "app.db")
    audit_db_path: str = str(BASE_DIR / "data" / "audit.db")
    upload_dir: str = str(BASE_DIR / "uploads")
    sample_kb_dir: str = str(BASE_DIR / "data" / "sample_kb")

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="forbid")




@lru_cache
def get_settings() -> Settings:
    return Settings()