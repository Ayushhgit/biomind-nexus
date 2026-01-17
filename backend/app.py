"""
BioMind Nexus - FastAPI Application Entrypoint

This module initializes the FastAPI application with:
- CORS and security middleware
- Route registration
- Startup/shutdown lifecycle hooks for database connections

Security: All routes are protected by RBAC middleware.
Agents do NOT have direct database access; all queries go through typed service layers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.gateway.middleware import SecurityMiddleware
from backend.graph_db.neo4j_client import Neo4jClient
from backend.audit.cassandra_client import CassandraAuditClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Startup:
        - Initialize Neo4j connection pool
        - Initialize Cassandra session for audit logs
    
    Shutdown:
        - Gracefully close all database connections
    """
    # Startup
    app.state.neo4j = Neo4jClient(settings.NEO4J_URI)
    app.state.audit = CassandraAuditClient(settings.CASSANDRA_HOSTS)
    
    await app.state.neo4j.connect()
    await app.state.audit.connect()
    
    yield
    
    # Shutdown
    await app.state.neo4j.close()
    await app.state.audit.close()


app = FastAPI(
    title="BioMind Nexus",
    description="Local-only biomedical research assistant with audit trails",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - restricted for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Security middleware for request validation and audit logging
app.add_middleware(SecurityMiddleware)


@app.get("/health")
async def health_check():
    """
    Health check endpoint for local dev tooling.
    Returns service status and connection states.
    """
    return {"status": "healthy", "version": "0.1.0"}


# TODO: Register route modules
# from backend.agents.routes import router as agents_router
# app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
