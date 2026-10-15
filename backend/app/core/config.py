from pydantic_settings import BaseSettings, SettingsConfigDict

# Shown in the UI and API docs. The product name is not decided; change it here only.
APP_NAME = "[BaSKom @ JOINTS]"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    stt_provider: str = "groq"
    llm_provider: str = "gemini"
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    stt_model: str = "whisper-large-v3"
    llm_model: str = ""

    database_url: str = "sqlite:///./data/app.db"
    upload_dir: str = "./data/uploads"
    frontend_origin: str = "http://localhost:5173"
    demo_mode: bool = True
    # Local development only: list profiles that have not passed their checks yet.
    show_untested_profiles: bool = False


settings = Settings()
