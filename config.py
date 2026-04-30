import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    FLASK_ENV  = os.getenv("FLASK_ENV", "development")
    DEBUG      = os.getenv("DEBUG", "True") == "True"
    SECRET_KEY = os.getenv("SECRET_KEY", "synaptia-secret-key-change-in-production")

    # Groq API (groq.com) — sole AI provider
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
    GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
