import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from backend.auth.database import get_engine, init_db
from backend.auth.models import User, Role
from backend.auth.password import hash_password

def upsert_user(session, email, password, role):
    # Check if exists
    statement = select(User).where(User.email == email)
    existing_user = session.exec(statement).first()
    
    if existing_user:
        print(f"User {email} already exists. Updating password/role.")
        existing_user.password_hash = hash_password(password)
        existing_user.role = role
        session.add(existing_user)
    else:
        print(f"Creating new user {email}...")
        new_user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True
        )
        session.add(new_user)

def main():
    print("Initializing database connection...")
    engine = get_engine()
    init_db(engine) # Ensure tables exist
    
    with Session(engine) as session:
        # Admin
        upsert_user(session, "admin@biomind.ai", "admin123", Role.ADMIN)
        
        # Researcher
        upsert_user(session, "researcher@biomind.ai", "research123", Role.RESEARCHER)
        
        session.commit()
        print("Credentials successfully added/updated.")

if __name__ == "__main__":
    main()
