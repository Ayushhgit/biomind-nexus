"""
BioMind Nexus - FastAPI Application Entrypoint

This module initializes the FastAPI application with:
- CORS and security middleware
- Authentication routes and dependencies
- Database lifecycle management
- Audit logging integration

Security: All routes are protected by RBAC middleware.
Agents do NOT have direct database access; all queries go through typed service layers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.gateway.middleware import SecurityMiddleware
from backend.auth.database import get_engine, init_db, get_session_factory
from backend.auth.routes import router as auth_router

# Optional imports (may fail due to dependencies)
try:
    from backend.graph_db.neo4j_client import Neo4jClient
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    Neo4jClient = None

try:
    from backend.audit.cassandra_client import CassandraAuditClient
    CASSANDRA_AVAILABLE = True
except (ImportError, Exception):
    CASSANDRA_AVAILABLE = False
    CassandraAuditClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Startup:
        - Initialize SQLModel database (Users, Sessions)
        - Initialize Neo4j connection pool
        - Initialize Cassandra session for audit logs
    
    Shutdown:
        - Gracefully close all database connections
    """
    # Initialize SQLModel database for auth
    engine = get_engine(settings.DATABASE_URL)
    init_db(engine)
    app.state.db_engine = engine
    app.state.db_session_factory = get_session_factory(engine)
    
    # Initialize optional services
    app.state.neo4j = None
    app.state.audit = None
    
    # Initialize Neo4j (optional)
    if NEO4J_AVAILABLE:
        try:
            app.state.neo4j = Neo4jClient(
                uri=settings.NEO4J_URI,
                user=settings.NEO4J_USER,
                password=settings.NEO4J_PASSWORD
            )
            await app.state.neo4j.connect()
            # Set the global client for DAL
            from backend.dal.neo4j_dal import set_neo4j_client
            set_neo4j_client(app.state.neo4j)
            print("Info: Neo4j connected and DAL initialized.")
        except Exception as e:
            print(f"Warning: Neo4j connection failed: {e}")
            app.state.neo4j = None
    else:
        print("Info: Neo4j driver not available, skipping.")
    
    # Initialize Cassandra (optional)
    if CASSANDRA_AVAILABLE:
        try:
            app.state.audit = CassandraAuditClient(settings.CASSANDRA_HOSTS)
            await app.state.audit.connect()
        except Exception as e:
            print(f"Warning: Cassandra connection failed: {e}")
            app.state.audit = None
    else:
        print("Info: Cassandra driver not available (Python 3.12+ incompatibility), skipping.")
    
    yield
    
    # Shutdown
    if app.state.neo4j:
        await app.state.neo4j.close()
    if app.state.audit:
        await app.state.audit.close()
    
    # Dispose SQLModel engine
    engine.dispose()


app = FastAPI(
    title="BioMind Nexus",
    description="Secure, AI-driven decision-support platform for drug repurposing",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - restricted for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Session-ID"],
)

# Security middleware for request validation and audit logging
app.add_middleware(SecurityMiddleware)


# Register authentication routes
app.include_router(auth_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """
    Health check endpoint for local dev tooling.
    Returns service status and connection states.
    """
    neo4j_healthy = False
    cassandra_healthy = False
    
    if app.state.neo4j:
        neo4j_healthy = await app.state.neo4j.health_check()
    
    if app.state.audit:
        cassandra_healthy = await app.state.audit.health_check()
    
    return {
        "status": "healthy",
        "version": "0.1.0",
        "services": {
            "database": True,  # SQLite/PostgreSQL always available
            "neo4j": neo4j_healthy,
            "cassandra": cassandra_healthy,
        }
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "BioMind Nexus",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# TODO: Register agent routes
# from backend.agents.routes import router as agents_router
# app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
