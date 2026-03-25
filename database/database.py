# database/database.py
"""
Database Connection and Session Management

Handles:
- SQLAlchemy engine creation with production settings
- Connection pooling for performance
- Session management with context managers
- Database initialization and migration
"""

from sqlalchemy import create_engine, event,text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import Pool
from contextlib import contextmanager
import time
import logging

from config.database_config import DatabaseConfig
from database.models import Base

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# ENGINE CREATION (Production-grade with connection pooling)
# ═══════════════════════════════════════════════════════════

# Get database URL and engine config
DATABASE_URL = DatabaseConfig.get_database_url()
ENGINE_CONFIG = DatabaseConfig.get_engine_config()

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    **ENGINE_CONFIG
)


# Connection pool event listeners (for monitoring)
@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when a new connection is created"""
    logger.debug("Database connection established")


@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool"""
    logger.debug("Connection checked out from pool")


# ═══════════════════════════════════════════════════════════
# SESSION FACTORY
# ═══════════════════════════════════════════════════════════

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


# ═══════════════════════════════════════════════════════════
# CONTEXT MANAGER (Safe transaction handling)
# ═══════════════════════════════════════════════════════════

@contextmanager
def get_db():
    """
    Database session context manager with automatic commit/rollback
    
    Usage:
        with get_db() as db:
            case = db.query(Case).filter_by(case_id='SAR-001').first()
            # Do work...
        # Automatic commit on success, rollback on exception
    
    This is PRODUCTION-GRADE - handles errors properly!
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise e
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ═══════════════════════════════════════════════════════════

def init_database(retry_count: int = 3, retry_delay: int = 2):
    """
    Initialize database - create all tables
    
    Args:
        retry_count: Number of retries if connection fails
        retry_delay: Seconds to wait between retries
    
    Production-grade with retry logic for reliability
    """
    for attempt in range(retry_count):
        try:
            logger.info(f"🔨 Creating database tables (attempt {attempt + 1}/{retry_count})...")
            
            # Create all tables defined in models.py
            Base.metadata.create_all(bind=engine)
            
            logger.info("✅ Database initialized successfully!")
            
            # Print created tables
            logger.info("\n📋 Created tables:")
            for table_name in Base.metadata.tables.keys():
                logger.info(f"   • {table_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {str(e)}")
            
            if attempt < retry_count - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("❌ Max retries reached. Database initialization failed.")
                raise e
    
    return False


def drop_all_tables():
    """
    Drop all tables (DANGEROUS - use with caution!)
    
    Only use in development or for testing
    """
    logger.warning("⚠️  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("✅ All tables dropped")


def reset_database():
    """
    Reset database - drop all tables and recreate
    
    DANGEROUS - only use in development!
    """
    logger.warning("⚠️  RESETTING DATABASE (drop + recreate)...")
    drop_all_tables()
    init_database()
    logger.info("✅ Database reset complete")


# ═══════════════════════════════════════════════════════════
# DATABASE HEALTH CHECK
# ═══════════════════════════════════════════════════════════

def check_database_connection() -> bool:
    """
    Check if database connection is working
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with get_db() as db:
            db.execute(text("SELECT 1"))
        logger.info("✅ Database connection healthy")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False


def get_connection_pool_status() -> dict:
    """
    Get current connection pool statistics
    
    Useful for monitoring in production
    """
    pool = engine.pool
    return {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'total_connections': pool.size() + pool.overflow()
    }


# ═══════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("DATABASE INITIALIZATION TEST")
    print("=" * 70)
    
    # Test database connection
    print("\n1️⃣  Testing database connection...")
    if check_database_connection():
        print("   ✅ Connection successful")
    else:
        print("   ❌ Connection failed")
        print("   💡 Make sure MySQL is running:")
        print("      brew services start mysql")
        exit(1)
    
    # Initialize database
    print("\n2️⃣  Initializing database...")
    init_database()
    
    # Check pool status
    print("\n3️⃣  Connection pool status:")
    pool_status = get_connection_pool_status()
    for key, value in pool_status.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 70)
    print("✅ DATABASE SETUP COMPLETE!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("   1. Verify tables in MySQL: mysql -u sar_user -p sar_generator")
    print("   2. Run: SHOW TABLES;")
    print("   3. Continue with database operations (operations.py)")
    print()