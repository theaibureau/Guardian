import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from passlib.hash import bcrypt
from models import Base, User

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///guardian.db")
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
            admin_email = os.getenv("FROM_EMAIL", "admin@example.com")
            u = User(
                username=admin_username,
                email=admin_email,
                full_name="Administrator",
                mobile=None,
                civil_defense_id="ADMIN",
                role="admin",
                status="active",
                is_subscribed=False,
                confirmation_token=None,
                password_hash=bcrypt.hash(admin_password),
            )
            db.add(u)
            db.commit()
