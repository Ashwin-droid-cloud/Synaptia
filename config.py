import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    FLASK_ENV      = os.getenv("FLASK_ENV", "development")
    DEBUG          = os.getenv("DEBUG", "True") == "True"
    SECRET_KEY     = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # xAI / Grok (Tier 1 — primary cloud)
    XAI_API_KEY     = os.getenv("XAI_API_KEY", "")
    XAI_MODEL       = os.getenv("XAI_MODEL", "grok-3-mini")

    # Gemini (Tier 2 — secondary cloud fallback)
    GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")

    # Ollama (Tier 3 — local last-resort fallback)
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
