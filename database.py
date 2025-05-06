from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import os

# Check if running in Docker (environment variable set in docker-compose.yml)
IN_DOCKER = os.environ.get('IN_DOCKER', '').lower() in ('true', '1', 't')

# Use the appropriate database URL based on environment
if IN_DOCKER:
    # When running in Docker, use the service name
    sqlAlchemyDatabaseUrl = f"postgresql://{settings.database_username}:{settings.database_password}@db:{settings.database_port}/{settings.database_name}"
else:
    # When running locally, use localhost
    sqlAlchemyDatabaseUrl = f"postgresql://{settings.database_username}:{settings.database_password}@localhost:{settings.database_port}/{settings.database_name}"

# Initialize the database engine
engine = create_engine(sqlAlchemyDatabaseUrl)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DatabaseSessionSingleton:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SessionLocal()  # Only create the session once
        return cls._instance


# Modify get_db to use the Singleton instance
def get_db():
    db = DatabaseSessionSingleton.get_instance()
    try:
        yield db
    finally:
        db.close()
