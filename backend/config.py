"""
BioMind Nexus - Configuration Management

Centralized configuration using Pydantic Settings.
All secrets and connection strings are loaded from environment variables.

Security: No secrets are hardcoded. Use .env for local development.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        NEO4J_URI: Bolt URI for local Neo4j instance
        NEO4J_USER: Neo4j authentication username
        NEO4J_PASSWORD: Neo4j authentication password
        CASSANDRA_HOSTS: Comma-separated list of Cassandra contact points
        CASSANDRA_KEYSPACE: Keyspace for audit logs
        SECRET_KEY: JWT signing key for authentication
        ALLOWED_ORIGINS: CORS allowed origins for local frontend
    """
    
    # Neo4j Configuration
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""  # Must be set via environment
    
    # Cassandra Configuration
    CASSANDRA_HOSTS: List[str] = ["127.0.0.1"]
    CASSANDRA_KEYSPACE: str = "biomind_audit"
    
    # Security
    SECRET_KEY: str = ""  # Must be set via environment
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived tokens
    SESSION_EXPIRE_HOURS: int = 24  # Server-side session duration
    
    # Database (PostgreSQL for production, SQLite for development)
    DATABASE_URL: str = "sqlite:///./biomind.db"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # LLM Configuration (for agents)
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4"
    LLM_API_KEY: str = ""  # Must be set via environment
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
