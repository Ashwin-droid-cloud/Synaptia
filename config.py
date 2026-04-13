import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    FLASK_ENV      = os.getenv("FLASK_ENV", "development")
    DEBUG          = os.getenv("DEBUG", "True") == "True"
    SECRET_KEY     = os.getenv("SECRET_KEY", "synaptia-secret-key-change-in-production")

    # Tier 1 — OpenRouter (primary cloud)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
    OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

    # Tier 2 — Google Gemini (secondary cloud fallback)
    GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")

    # Tier 3 — Ollama (local last-resort fallback)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3:8b")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig
}
