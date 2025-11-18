#!/usr/bin/env python3
"""Initialize the database schema."""
import os
from models import Base
from storage import engine

if __name__ == "__main__":
    if not engine:
        print("ERROR: DATABASE_URL not set. Cannot initialize database.")
        exit(1)
    
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("Database tables created successfully!")
    
    # List all created tables
    print("\nCreated tables:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")
