"""
BioMind Nexus - Neo4j Client

Async client for Neo4j graph database operations.
All graph queries are issued through this client.

Architecture:
- Connection pooling for performance
- Typed query results
- Transaction management
- Query logging for audit

Security: Only this module has direct Neo4j access.
Agents access graph data through the service layer.
"""

from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession


class Neo4jClient:
    """
    Async Neo4j client with connection pooling.
    
    Usage:
        client = Neo4jClient("bolt://localhost:7687")
        await client.connect()
        
        async with client.session() as session:
            result = await session.run("MATCH (n) RETURN n LIMIT 10")
            nodes = await result.data()
        
        await client.close()
    """
    
    def __init__(
        self, 
        uri: str,
        user: str = "neo4j",
        password: str = "",
        database: str = "neo4j"
    ):
        """
        Initialize client configuration.
        
        Args:
            uri: Bolt URI for Neo4j instance
            user: Authentication username
            password: Authentication password
            database: Target database name
        """
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._driver: Optional[AsyncDriver] = None
    
    async def connect(self) -> None:
        """
        Establish connection pool to Neo4j.
        
        Call this during application startup.
        """
        self._driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
        )
        # Verify connectivity
        await self._driver.verify_connectivity()
    
    async def close(self) -> None:
        """
        Close all connections in the pool.
        
        Call this during application shutdown.
        """
        if self._driver:
            await self._driver.close()
            self._driver = None
    
    @asynccontextmanager
    async def session(self) -> AsyncSession:
        """
        Get a session from the connection pool.
        
        Usage:
            async with client.session() as session:
                result = await session.run(query)
        """
        if not self._driver:
            raise RuntimeError("Neo4j client not connected. Call connect() first.")
        
        session = self._driver.session(database=self._database)
        try:
            yield session
        finally:
            await session.close()
    
    async def execute_read(self, query: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        Execute a read query and return results.
        
        Args:
            query: Cypher query string
            params: Query parameters
        
        Returns:
            List of result records as dicts
        """
        async with self.session() as session:
            result = await session.run(query, params or {})
            return await result.data()
    
    async def execute_write(self, query: str, params: Dict[str, Any] = None) -> Dict:
        """
        Execute a write query within a transaction.
        
        Args:
            query: Cypher query string
            params: Query parameters
        
        Returns:
            Summary of the write operation
        """
        async with self.session() as session:
            result = await session.run(query, params or {})
            summary = await result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "relationships_created": summary.counters.relationships_created,
                "properties_set": summary.counters.properties_set,
            }
    
    async def health_check(self) -> bool:
        """
        Check if Neo4j connection is healthy.
        
        Returns:
            True if connected and responsive
        """
        try:
            async with self.session() as session:
                await session.run("RETURN 1")
            return True
        except Exception:
            return False
