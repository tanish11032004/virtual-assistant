from functools import wraps
from typing import Callable, Any
from flask import request, current_app
import time
import structlog

logger = structlog.get_logger()

def log_execution_time(f: Callable) -> Callable:
    """Decorator to log function execution time."""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start_time
        logger.info(
            "function_execution",
            function=f.__name__,
            duration=f"{duration:.2f}s"
        )
        return result
    return decorated_function

def validate_api_key(f: Callable) -> Callable:
    """Decorator to validate API key for external API endpoints."""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != current_app.config['API_KEY']:
            return {'error': 'Invalid API key'}, 401
        return f(*args, **kwargs)
    return decorated_function
