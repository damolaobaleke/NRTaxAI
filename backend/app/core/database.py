"""
Database connection and session management
"""

import databases
import structlog
from app.core.config import settings

logger = structlog.get_logger()

# Global database connection
database: databases.Database = None


async def get_database() -> databases.Database:
    """Get database connection"""
    global database
    if database is None:
        database = databases.Database(settings.DATABASE_URL)
        await database.connect()
        logger.info("Database connected")
    return database


async def close_database():
    """Close database connection"""
    global database
    if database:
        await database.disconnect()
        logger.info("Database disconnected")
