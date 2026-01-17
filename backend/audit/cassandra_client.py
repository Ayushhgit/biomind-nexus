"""
BioMind Nexus - Cassandra Audit Client

Async client for append-only audit logging to Apache Cassandra.
All system actions are logged here for compliance and traceability.

Design Principles:
- Append-only: No updates or deletes
- Hash-chained: Each entry links to previous for integrity
- Time-partitioned: Optimized for time-range queries

Security: Audit logs are immutable. Tampering is detectable via hash chain.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from cassandra.cluster import Cluster, Session
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import SimpleStatement, ConsistencyLevel


class CassandraAuditClient:
    """
    Async-compatible Cassandra client for audit logging.
    
    Note: cassandra-driver is synchronous, but we wrap for async interface.
    For production, consider using acsylla or run in thread pool.
    
    Usage:
        client = CassandraAuditClient(["127.0.0.1"])
        await client.connect()
        
        await client.log_event(
            event_type="query",
            user_id="user123",
            action="invoke_agent",
            details={"agent": "literature"}
        )
        
        await client.close()
    """
    
    def __init__(
        self,
        hosts: List[str],
        keyspace: str = "biomind_audit",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize client configuration.
        
        Args:
            hosts: List of Cassandra contact points
            keyspace: Target keyspace for audit logs
            username: Optional authentication username
            password: Optional authentication password
        """
        self._hosts = hosts
        self._keyspace = keyspace
        self._username = username
        self._password = password
        self._cluster: Optional[Cluster] = None
        self._session: Optional[Session] = None
    
    async def connect(self) -> None:
        """
        Establish connection to Cassandra cluster.
        
        Creates keyspace and tables if they don't exist.
        """
        auth_provider = None
        if self._username and self._password:
            auth_provider = PlainTextAuthProvider(
                username=self._username,
                password=self._password
            )
        
        self._cluster = Cluster(
            contact_points=self._hosts,
            auth_provider=auth_provider,
        )
        self._session = self._cluster.connect()
        
        # Initialize schema
        await self._initialize_schema()
    
    async def close(self) -> None:
        """Close cluster connection."""
        if self._cluster:
            self._cluster.shutdown()
            self._cluster = None
            self._session = None
    
    async def _initialize_schema(self) -> None:
        """Create keyspace and tables if not exists."""
        # Create keyspace
        self._session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {self._keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """)
        
        self._session.set_keyspace(self._keyspace)
        
        # Create audit_events table (time-partitioned)
        self._session.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                partition_date date,
                event_id timeuuid,
                event_type text,
                user_id text,
                request_id text,
                action text,
                resource text,
                details text,
                hash text,
                prev_hash text,
                created_at timestamp,
                PRIMARY KEY ((partition_date), event_id)
            ) WITH CLUSTERING ORDER BY (event_id DESC)
        """)
        
        # Create index for request_id lookups
        self._session.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_request_id 
            ON audit_events (request_id)
        """)
        
        # Create index for user_id lookups
        self._session.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_user_id 
            ON audit_events (user_id)
        """)
    
    async def log_event(
        self,
        event_type: str,
        user_id: str,
        action: str,
        request_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Append a new audit event.
        
        Args:
            event_type: Category (auth, query, action, error)
            user_id: ID of user performing action
            action: Action being performed
            request_id: Correlating request ID
            resource: Target resource (if applicable)
            details: Additional event metadata
        
        Returns:
            Event ID (timeuuid string)
        """
        from backend.audit.hash_chain import compute_event_hash, get_latest_hash
        
        event_id = uuid.uuid1()
        partition_date = datetime.utcnow().date()
        created_at = datetime.utcnow()
        
        # Get previous hash for chain
        prev_hash = await get_latest_hash(self._session, partition_date)
        
        # Compute hash for this event
        event_hash = compute_event_hash(
            event_id=str(event_id),
            event_type=event_type,
            user_id=user_id,
            action=action,
            prev_hash=prev_hash,
        )
        
        import json
        details_json = json.dumps(details) if details else "{}"
        
        statement = SimpleStatement(
            """
            INSERT INTO audit_events 
                (partition_date, event_id, event_type, user_id, request_id, 
                 action, resource, details, hash, prev_hash, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            consistency_level=ConsistencyLevel.LOCAL_QUORUM
        )
        
        self._session.execute(statement, [
            partition_date,
            event_id,
            event_type,
            user_id,
            request_id or "",
            action,
            resource or "",
            details_json,
            event_hash,
            prev_hash,
            created_at,
        ])
        
        return str(event_id)
    
    async def get_events(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query audit events within a time range.
        
        Args:
            start_date: Start of query range
            end_date: End of query range
            user_id: Optional filter by user
            event_type: Optional filter by event type
            limit: Maximum number of results
            
        Returns:
            List of audit event dictionaries
        """
        import json
        from datetime import timedelta
        
        events = []
        current_date = start_date.date()
        end = end_date.date()
        
        while current_date <= end and len(events) < limit:
            try:
                # Query each partition (date)
                query = """
                    SELECT partition_date, event_id, event_type, user_id, 
                           request_id, action, resource, details, hash, 
                           prev_hash, created_at 
                    FROM audit_events 
                    WHERE partition_date = %s 
                    LIMIT %s
                """
                
                results = self._session.execute(query, [current_date, limit - len(events)])
                
                for row in results:
                    # Apply filters
                    if user_id and row.user_id != user_id:
                        continue
                    if event_type and row.event_type != event_type:
                        continue
                    
                    # Parse details JSON
                    details = {}
                    if row.details:
                        try:
                            details = json.loads(row.details)
                        except:
                            details = {"raw": row.details}
                    
                    events.append({
                        "event_id": str(row.event_id),
                        "partition_date": str(row.partition_date),
                        "event_type": row.event_type,
                        "user_id": row.user_id,
                        "request_id": row.request_id or "",
                        "action": row.action,
                        "resource": row.resource or "",
                        "details": details,
                        "created_at": row.created_at.isoformat() if row.created_at else "",
                        "hash": row.hash or "",
                    })
                    
                    if len(events) >= limit:
                        break
                        
            except Exception as e:
                print(f"Error querying Cassandra for date {current_date}: {e}")
            
            current_date = current_date + timedelta(days=1)
        
        return events
    
    async def get_recent_events(
        self,
        limit: int = 50,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recent audit events (last 7 days).
        Convenience method for admin dashboard.
        """
        from datetime import timedelta
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        return await self.get_events(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            event_type=event_type,
            limit=limit
        )

    async def get_events_by_request(
        self,
        request_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all audit events for a specific request.
        """
        statement = SimpleStatement(
            f"SELECT * FROM audit_events WHERE request_id = %s",
            consistency_level=ConsistencyLevel.LOCAL_QUORUM
        )
        
        results = self._session.execute(statement, [request_id])
        
        events = []
        for row in results:
            import json
            details = {}
            if row.details:
                try:
                    details = json.loads(row.details)
                except:
                    pass
            
            events.append({
                "event_id": str(row.event_id),
                "event_type": row.event_type,
                "user_id": row.user_id,
                "action": row.action,
                "timestamp": row.created_at.isoformat() if row.created_at else "",
                "details": details
            })
            
        return events
    
    async def verify_chain_integrity(self, date: datetime) -> bool:
        """
        Verify hash chain integrity for a given date.
        
        Returns:
            True if chain is valid, False if tampering detected
        """
        from backend.audit.hash_chain import verify_chain
        return await verify_chain(self._session, date.date())
    
    async def health_check(self) -> bool:
        """Check if Cassandra connection is healthy."""
        try:
            self._session.execute("SELECT now() FROM system.local")
            return True
        except Exception:
            return False
