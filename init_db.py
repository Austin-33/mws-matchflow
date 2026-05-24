"""
Run this once to create the database and tables.
Usage: python init_db.py
"""
from app import app
from extensions import db
import models  # noqa: F401 — registers all ORM models

with app.app_context():
    db.create_all()
    print("✅ Database created successfully!")
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    print("   Tables:", inspector.get_table_names())
