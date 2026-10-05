import logging

from pydantic_settings import BaseSettings

_DEFAULT_JWT_SECRET = "change_this_to_a_long_random_string"


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "carag_db"

    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # --- Auth: password rules, password reset, reset emails ---
    min_password_length: int = 8
    reset_token_expire_minutes: int = 10
    frontend_url: str = "http://localhost:5173"  # base URL used in the reset-password email link
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_user: str = ""  # SMTP login / sender address
    email_pass: str = ""  # SMTP password (for Gmail: an app password)

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    llm_timeout: int = 300
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    embedding_model: str = "all-MiniLM-L6-v2"

    max_chunk_tokens: int = 500
    min_chunk_tokens: int = 100
    semantic_threshold: float = 0.30

    validation_similarity_threshold: float = 0.55

    # Max number of candidate-answer LLM calls run at once during CA-RAG
    # validation. Only affects speed, never which chunks are validated.
    # Set to 1 to reproduce the original strictly sequential behaviour.
    carag_validation_concurrency: int = 4

    vector_store_dir: str = "./vector_store"
    upload_dir: str = "./uploads"

    class Config:
        env_file = ".env"


settings = Settings()

if settings.jwt_secret == _DEFAULT_JWT_SECRET:
    logging.getLogger("uvicorn.error").warning(
        "JWT_SECRET is still the placeholder value. Set a long random JWT_SECRET in backend/.env "
        "-- anyone who knows the placeholder can forge login tokens."
    )
