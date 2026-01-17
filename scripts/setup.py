"""
BioMind Nexus - Complete Setup Script

One-command setup for all databases and initial data.
Checks prerequisites and provides helpful error messages.

Usage:
    python scripts/setup.py

Prerequisites:
    - Docker installed and running
    - Python dependencies installed (pip install -r backend/requirements.txt)
"""

import subprocess
import sys
import time
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_step(step: int, text: str):
    """Print a numbered step."""
    print(f"\n[{step}] {text}")


def run_command(cmd: str, check: bool = True) -> tuple:
    """Run a shell command and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def check_docker():
    """Check if Docker is available."""
    code, _, _ = run_command("docker --version")
    return code == 0


def check_docker_compose():
    """Check if Docker Compose is available."""
    code, _, _ = run_command("docker compose version")
    if code != 0:
        code, _, _ = run_command("docker-compose --version")
    return code == 0


def start_neo4j():
    """Start Neo4j using Docker Compose."""
    print("  Starting Neo4j container...")
    
    # Check if already running
    code, stdout, _ = run_command("docker ps --filter name=biomind-neo4j --format {{.Names}}")
    if "biomind-neo4j" in stdout:
        print("  ✓ Neo4j already running")
        return True
    
    # Start with docker compose
    code, stdout, stderr = run_command("docker compose up -d neo4j")
    if code != 0:
        # Try docker-compose (older syntax)
        code, stdout, stderr = run_command("docker-compose up -d neo4j")
    
    if code != 0:
        print(f"  ✗ Failed to start Neo4j: {stderr}")
        return False
    
    print("  ⏳ Waiting for Neo4j to be ready...")
    for i in range(30):
        time.sleep(2)
        code, _, _ = run_command("docker exec biomind-neo4j wget -q --spider http://localhost:7474 2>/dev/null || curl -sf http://localhost:7474 > /dev/null 2>&1")
        if code == 0:
            print("  ✓ Neo4j is ready")
            return True
        print(f"    Waiting... ({i+1}/30)")
    
    print("  ✗ Neo4j took too long to start")
    return False


def wait_for_neo4j():
    """Wait for Neo4j to be fully ready."""
    import asyncio
    
    async def check():
        from backend.config import settings
        from backend.graph_db.neo4j_client import Neo4jClient
        
        client = Neo4jClient(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD or "biomind2024",
        )
        
        for i in range(15):
            try:
                await client.connect()
                await client.close()
                return True
            except Exception:
                time.sleep(2)
        return False
    
    return asyncio.run(check())


def init_neo4j_schema():
    """Initialize Neo4j schema."""
    print("  Initializing Neo4j schema...")
    code, stdout, stderr = run_command("python scripts/init_neo4j.py")
    if code != 0:
        print(f"  ⚠ Schema init warning: {stderr}")
    else:
        print("  ✓ Schema initialized")
    return True


def seed_knowledge_graph():
    """Seed the knowledge graph with sample data."""
    print("  Seeding knowledge graph...")
    code, stdout, stderr = run_command("python scripts/seed_knowledge_graph.py")
    if code != 0:
        print(f"  ⚠ Seed warning: {stderr}")
    print(stdout)
    return True


def init_auth_db():
    """Initialize the auth database."""
    print("  Initializing auth database...")
    code, stdout, stderr = run_command("python scripts/seed_users.py")
    print(stdout)
    return True


def create_env_file():
    """Create .env file from template if it doesn't exist."""
    env_path = Path(__file__).parent.parent / ".env"
    example_path = Path(__file__).parent.parent / ".env.example"
    
    if env_path.exists():
        print("  ✓ .env file already exists")
        return True
    
    if not example_path.exists():
        print("  ✗ .env.example not found")
        return False
    
    import shutil
    shutil.copy(example_path, env_path)
    print("  ✓ Created .env from template")
    print("  ⚠ Please edit .env and set your API keys!")
    return True


def main():
    print_header("BioMind Nexus - Setup")
    print("\nThis script will set up all required databases.\n")
    
    # Step 1: Check prerequisites
    print_step(1, "Checking prerequisites...")
    
    if not check_docker():
        print("  ✗ Docker not found. Please install Docker Desktop.")
        print("    https://www.docker.com/products/docker-desktop/")
        return 1
    print("  ✓ Docker available")
    
    if not check_docker_compose():
        print("  ✗ Docker Compose not found.")
        return 1
    print("  ✓ Docker Compose available")
    
    # Step 2: Create .env file
    print_step(2, "Setting up configuration...")
    create_env_file()
    
    # Step 3: Start Neo4j
    print_step(3, "Starting Neo4j...")
    if not start_neo4j():
        print("\n⚠ Could not start Neo4j automatically.")
        print("   Try manually: docker compose up -d")
        return 1
    
    # Wait for Neo4j to be fully ready
    print("  Waiting for Neo4j to accept connections...")
    time.sleep(5)  # Give it a moment
    
    # Step 4: Initialize Neo4j schema
    print_step(4, "Initializing Neo4j schema...")
    init_neo4j_schema()
    
    # Step 5: Seed knowledge graph
    print_step(5, "Seeding knowledge graph...")
    seed_knowledge_graph()
    
    # Step 6: Initialize auth database
    print_step(6, "Initializing auth database...")
    init_auth_db()
    
    # Done!
    print_header("Setup Complete!")
    print("""
Next steps:
  1. Edit .env and add your GROQ_API_KEY
  2. Start the server:
     cd c:\\Projects\\biomind-nexus
     uvicorn backend.app:app --reload
     
  3. Open the API docs:
     http://localhost:8000/docs

  4. Open Neo4j Browser:
     http://localhost:7474
     Username: neo4j
     Password: biomind2024
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
