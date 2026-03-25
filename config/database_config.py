# config/database_config.py
"""
Database Configuration for SAR Generator
Production-grade configuration with environment variable management
"""

import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()


class DatabaseConfig:
    """
    Database configuration class with production settings
    Manages MySQL connection parameters and SQLAlchemy engine config
    """
    
    # MySQL Connection Parameters
    MYSQL_USER: str = os.getenv('MYSQL_USER', 'sar_user')
    MYSQL_PASSWORD: str = os.getenv('MYSQL_PASSWORD', 'SAR_secure_2024!')
    MYSQL_HOST: str = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT: str = os.getenv('MYSQL_PORT', '3306')
    MYSQL_DATABASE: str = os.getenv('MYSQL_DATABASE', 'sar_generator')
    
    # Build Database URL for SQLAlchemy
    DATABASE_URL: str = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        f"?charset=utf8mb4"
    )
    
    # SQLAlchemy Engine Configuration (Production-grade)
    SQLALCHEMY_ECHO: bool = os.getenv('SQLALCHEMY_ECHO', 'False').lower() == 'true'
    SQLALCHEMY_POOL_SIZE: int = int(os.getenv('SQLALCHEMY_POOL_SIZE', '5'))
    SQLALCHEMY_MAX_OVERFLOW: int = int(os.getenv('SQLALCHEMY_MAX_OVERFLOW', '10'))
    SQLALCHEMY_POOL_RECYCLE: int = int(os.getenv('SQLALCHEMY_POOL_RECYCLE', '3600'))
    SQLALCHEMY_POOL_PRE_PING: bool = True  # Test connection before use
    SQLALCHEMY_POOL_TIMEOUT: int = 30
    
    # Connection retry settings
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2
    
    @classmethod
    def get_database_url(cls, testing: bool = False) -> str:
        """Get database URL for given environment"""
        if testing:
            return "sqlite:///test_sar.db"
        return cls.DATABASE_URL
    
    @classmethod
    def get_engine_config(cls) -> dict:
        """Get SQLAlchemy engine configuration dictionary"""
        return {
            'echo': cls.SQLALCHEMY_ECHO,
            'pool_size': cls.SQLALCHEMY_POOL_SIZE,
            'max_overflow': cls.SQLALCHEMY_MAX_OVERFLOW,
            'pool_recycle': cls.SQLALCHEMY_POOL_RECYCLE,
            'pool_pre_ping': cls.SQLALCHEMY_POOL_PRE_PING,
            'pool_timeout': cls.SQLALCHEMY_POOL_TIMEOUT,
        }
    
    @classmethod
    def print_config(cls, mask_password: bool = True) -> None:
        """Print current configuration (with optional password masking)"""
        password_display = '*' * len(cls.MYSQL_PASSWORD) if mask_password else cls.MYSQL_PASSWORD
        
        print("=" * 70)
        print("DATABASE CONFIGURATION")
        print("=" * 70)
        print(f"Host:           {cls.MYSQL_HOST}:{cls.MYSQL_PORT}")
        print(f"Database:       {cls.MYSQL_DATABASE}")
        print(f"User:           {cls.MYSQL_USER}")
        print(f"Password:       {password_display}")
        print(f"Pool Size:      {cls.SQLALCHEMY_POOL_SIZE}")
        print(f"Max Overflow:   {cls.SQLALCHEMY_MAX_OVERFLOW}")
        print(f"Pool Recycle:   {cls.SQLALCHEMY_POOL_RECYCLE}s")
        print(f"Echo SQL:       {cls.SQLALCHEMY_ECHO}")
        print("=" * 70)


class LLMConfig:
    """
    LLM Configuration
    Manages settings for local Llama 3 or template-based generation
    """
    
    LLM_MODE: str = os.getenv('LLM_MODE', 'template')
    # Options: 'llama' (local model), 'template' (fast fallback), 'api' (external)
    
    LLAMA_MODEL_PATH: Optional[str] = os.getenv('LLAMA_MODEL_PATH')
    LLAMA_N_CTX: int = int(os.getenv('LLAMA_N_CTX', '4096'))  # Context window size
    LLAMA_N_THREADS: int = int(os.getenv('LLAMA_N_THREADS', '4'))  # CPU threads
    LLAMA_TEMPERATURE: float = 0.3  # Lower = more factual, Higher = more creative
    LLAMA_MAX_TOKENS: int = 3000  # Maximum narrative length
    
    @classmethod
    def print_config(cls) -> None:
        """Print LLM configuration"""
        print("=" * 70)
        print("LLM CONFIGURATION")
        print("=" * 70)
        print(f"Mode:           {cls.LLM_MODE}")
        print(f"Model Path:     {cls.LLAMA_MODEL_PATH or 'Not set (using template mode)'}")
        print(f"Context Size:   {cls.LLAMA_N_CTX}")
        print(f"Threads:        {cls.LLAMA_N_THREADS}")
        print(f"Temperature:    {cls.LLAMA_TEMPERATURE}")
        print(f"Max Tokens:     {cls.LLAMA_MAX_TOKENS}")
        print("=" * 70)


# Convenience functions for easy imports
def get_database_url() -> str:
    """Get database connection URL"""
    return DatabaseConfig.get_database_url()


def get_engine_config() -> dict:
    """Get SQLAlchemy engine configuration"""
    return DatabaseConfig.get_engine_config()


# Test configuration if run directly
if __name__ == '__main__':
    print("\n🔍 Testing Configuration...\n")
    DatabaseConfig.print_config()
    print()
    LLMConfig.print_config()