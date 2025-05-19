import psycopg2
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from settings.config import CONFIG

DATABASE_URL = CONFIG.DATABASE_URL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


postgres_url = CONFIG.DATABASE_URL

# Create a SQLAlchemy Engine
engine = create_engine(postgres_url)
# Create a session
Session = sessionmaker(bind=engine)


def get_db_session():
    """SQL Alchemy session object"""
    session = Session()
    return session


def get_db_connection():
    """Postgres database connection object"""
    try:
        conn = psycopg2.connect(dsn=postgres_url)
        yield conn
    finally:
        conn.close()


# For celery worker
def get_db_connection_eager():
    """Postgres database connection object"""
    conn = psycopg2.connect(dsn=postgres_url)
    return conn


# Exception handler for database connection errors
def handle_db_connection_error():
    raise HTTPException(status_code=500, detail="Database connection error")
