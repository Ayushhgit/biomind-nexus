"""
Centralized configuration using Pydantic Settings.
All secrets and connection strings are loaded from environment variables.

"""

from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # Neo4j Configuration
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    
    # Cassandra Configuration
    CASSANDRA_HOSTS: List[str] = ["127.0.0.1"]
    CASSANDRA_KEYSPACE: str = "biomind_audit"
    
    # Security
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived tokens
    SESSION_EXPIRE_HOURS: int = 24  # Server-side session duration
    
    # Database (PostgreSQL for production, SQLite for development)
    DATABASE_URL: str = "sqlite:///./biomind.db"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Groq API Configuration
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    
    # PubMed API Configuration 
    PUBMED_EMAIL: str = ""
    PUBMED_MAX_RESULTS: int = 20
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
