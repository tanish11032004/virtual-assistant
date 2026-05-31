from typing import Dict, Any
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """Application configuration."""
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'default-secret-key')
    MYSQL_HOST: str = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER: str = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD: str = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB: str = os.getenv('MYSQL_DB', 'virtual_assistant_users')
    
    # Cache configuration
    CACHE_TYPE: str = 'redis'
    CACHE_REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT: int = 300
    
    # Rate limiting
    RATELIMIT_DEFAULT: str = "200 per day"
    RATELIMIT_STORAGE_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND: str = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

    @staticmethod
    def to_dict() -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            key: getattr(Config, key)
            for key in dir(Config)
            if not key.startswith('_') and not callable(getattr(Config, key))
        }

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG: bool = True
    TESTING: bool = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG: bool = False
    TESTING: bool = False
    
    # Override with more secure settings
    RATELIMIT_DEFAULT: str = "100 per day"

class TestingConfig(Config):
    """Testing configuration."""
    TESTING: bool = True
    DEBUG: bool = True
    MYSQL_DB: str = 'virtual_assistant_test'

# Configuration dictionary
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
