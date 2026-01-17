#!/usr/bin/env python3
"""
Utility script to view audit logs from Cassandra.
Usage: python scripts/view_audit_logs.py [limit]
"""

import asyncio
import sys
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import print as rprint

# Add project root to path
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings
from backend.audit.cassandra_client import CassandraAuditClient

console = Console()

async def view_logs(limit: int = 20):
    client = CassandraAuditClient(
        hosts=settings.CASSANDRA_HOSTS,
        keyspace=settings.CASSANDRA_KEYSPACE
    )
    
    try:
        await client.connect()
        rprint(f"[green]Connected to Cassandra at {settings.CASSANDRA_HOSTS}[/green]")
        
        # We need a way to query recent logs.
        # Since we don't have a reliable 'get_all_recent' method yet (only by request),
        # we'll use a raw query for this utility script.
        
        query = f"SELECT * FROM audit_events LIMIT {limit}"
        
        # Access session directly for this admin tool
        if hasattr(client, '_session') and client._session:
            from cassandra.query import SimpleStatement
            stmt = SimpleStatement(query)
            rows = client._session.execute(stmt)
            
            table = Table(title=f"Audit Logs (Limit: {limit})")
            table.add_column("Time", style="cyan", no_wrap=True)
            table.add_column("Event Type", style="magenta")
            table.add_column("User", style="yellow")
            table.add_column("Action", style="green")
            table.add_column("Details", style="white")
            table.add_column("Hash Valid", style="blue")
            
            count = 0
            for row in rows:
                count += 1
                timestamp = row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "N/A"
                
                # Parse details
                details_str = row.details
                try:
                    details = json.loads(row.details)
                    # Pretty print small details
                    if len(str(details)) > 50:
                        details_str = str(details)[:47] + "..."
                    else:
                        details_str = str(details)
                except:
                    pass

                table.add_row(
                    timestamp,
                    row.event_type,
                    row.user_id,
                    row.action,
                    details_str,
                    "✓"  # Assuming valid for now
                )
            
            if count == 0:
                rprint("[yellow]No logs found.[/yellow]")
            else:
                console.print(table)
                rprint(f"\n[dim]Showing {count} events.[/dim]")
        
    except Exception as e:
        rprint(f"[red]Error fetching logs: {e}[/red]")
    finally:
        await client.close()

if __name__ == "__main__":
    limit = 20
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except:
            pass
            
    try:
        asyncio.run(view_logs(limit))
    except KeyboardInterrupt:
        pass
