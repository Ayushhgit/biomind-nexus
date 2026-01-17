"""
BioMind Nexus - Database Seed Script

Creates initial admin user for development.

Usage:
    python -m scripts.seed_users
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from sqlmodel import Session

from backend.config import settings
from backend.auth.database import get_engine, init_db
from backend.auth.models import User, Role
from backend.auth.password import hash_password


def seed_admin_user():
    """Create default admin user for development."""
    engine = get_engine(settings.DATABASE_URL)
    init_db(engine)
    
    with Session(engine) as session:
        # Check if admin already exists
        from sqlmodel import select
        existing = session.exec(
            select(User).where(User.email == "admin@biomind.local")
        ).first()
        
        if existing:
            print("Admin user already exists.")
            return
        
        # Create admin user
        now = datetime.utcnow()
        admin = User(
            email="admin@biomind.local",
            password_hash=hash_password("Admin@BioMind2024"),
            role=Role.ADMIN,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        session.add(admin)
        session.commit()
        
        print("Admin user created successfully!")
        print(f"  Email: admin@biomind.local")
        print(f"  Password: Admin@BioMind2024")
        print(f"  Role: admin")


def seed_demo_users():
    """Create demo users for all roles."""
    engine = get_engine(settings.DATABASE_URL)
    init_db(engine)
    
    demo_users = [
        ("researcher@biomind.local", "Research@2024", Role.RESEARCHER),
        ("reviewer@biomind.local", "Reviewer@2024", Role.REVIEWER),
        ("auditor@biomind.local", "Auditor@2024", Role.AUDITOR),
    ]
    
    with Session(engine) as session:
        for email, password, role in demo_users:
            from sqlmodel import select
            existing = session.exec(
                select(User).where(User.email == email)
            ).first()
            
            if existing:
                print(f"User {email} already exists.")
                continue
            
            now = datetime.utcnow()
            user = User(
                email=email,
                password_hash=hash_password(password),
                role=role,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            
            session.add(user)
            print(f"Created user: {email} ({role.value})")
        
        session.commit()


if __name__ == "__main__":
    print("=" * 50)
    print("BioMind Nexus - User Seed Script")
    print("=" * 50)
    
    seed_admin_user()
    
    print()
    response = input("Create demo users for all roles? (y/n): ")
    if response.lower() == "y":
        seed_demo_users()
    
    print()
    print("Done!")
