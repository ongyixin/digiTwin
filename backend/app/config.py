from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "digitwin2026"

    gemini_api_key: str = ""

    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 3072
    chat_model: str = "gemini-2.5-flash"
    llm_provider: str = "gemini"
    pii_redaction_enabled: bool = False

    environment: str = "development"

    # Transcription provider: "gemini" (default) or "openai"
    transcription_provider: str = "gemini"
    openai_api_key: str = ""
    openai_transcription_model: str = "gpt-4o-transcribe-diarize"

    # GitHub integration
    github_access_token: str = ""
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_installation_id: str = ""
    github_webhook_secret: str = ""

    # RocketRide pipeline engine
    # Set ROCKETRIDE_URI (e.g. ws://localhost:5565) to enable delegated pipeline
    # execution. When empty the backend falls back to in-process execution.
    rocketride_uri: str = ""
    rocketride_apikey: str = ""

    # Absolute path to the pipelines/ directory. Auto-detected when empty.
    pipelines_dir: str = ""


settings = Settings()
