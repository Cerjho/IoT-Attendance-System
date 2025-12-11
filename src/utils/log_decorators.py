"""
Logging Decorators for Performance and Context Tracking
"""

import functools
import logging
import time
from typing import Callable, Any, Optional
from contextvars import ContextVar

from .structured_logging import set_correlation_id

# Context variable for operation tracking
current_operation: ContextVar[Optional[str]] = ContextVar("current_operation", default=None)


def log_execution_time(
    logger: Optional[logging.Logger] = None,
    level: int = logging.INFO,
    slow_threshold_ms: float = 1000.0
):
    """
    Decorator to log function execution time
    
    Args:
        logger: Logger to use (defaults to function's module logger)
        level: Log level for normal execution
        slow_threshold_ms: Log as WARNING if execution exceeds this
    
    Example:
        @log_execution_time
        def process_image(frame):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            # Track execution time
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                
                # Only log if exceeds threshold or at DEBUG level
                if elapsed_ms > slow_threshold_ms:
                    # Slow operation - log as warning
                    logger.warning(
                        f"{func.__name__} slow execution",
                        extra={
                            "function": func.__name__,
                            "duration_ms": round(elapsed_ms, 2),
                            "threshold_ms": slow_threshold_ms
                        }
                    )
                elif logger.isEnabledFor(logging.DEBUG):
                    # Fast operation - only log at debug level
                    logger.debug(
                        f"{func.__name__} completed",
                        extra={
                            "function": func.__name__,
                            "duration_ms": round(elapsed_ms, 2)
                        }
                    )
        
        return wrapper
    return decorator


def log_with_context(
    operation: str,
    logger: Optional[logging.Logger] = None,
    include_args: bool = False
):
    """
    Decorator to add operation context to all nested log calls
    
    Args:
        operation: Operation name to track
        logger: Logger to use
        include_args: Include function arguments in log context
    
    Example:
        @log_with_context(operation="face_detection")
        def detect_face(frame, student_id):
            logger.info("Processing...")  # Will include operation context
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Set operation context
            token = current_operation.set(operation)
            
            # Get logger
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            # Build context
            context = {
                "operation": operation,
                "function": func.__name__
            }
            
            # Add args if requested
            if include_args:
                # Get function signature
                import inspect
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                # Add non-sensitive args
                for key, value in bound_args.arguments.items():
                    if not key.startswith('_') and key not in ['password', 'token', 'key']:
                        context[f"arg_{key}"] = str(value)[:100]  # Limit length
            
            logger.debug(f"Starting {operation}", extra=context)
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Completed {operation}", extra={**context, "status": "success"})
                return result
            except Exception as e:
                logger.error(
                    f"Failed {operation}: {str(e)}",
                    extra={**context, "status": "error", "error_type": type(e).__name__},
                    exc_info=True
                )
                raise
            finally:
                # Reset context
                current_operation.reset(token)
        
        return wrapper
    return decorator


def log_exceptions(
    logger: Optional[logging.Logger] = None,
    reraise: bool = True,
    default_return: Any = None
):
    """
    Decorator to log exceptions with full context
    
    Args:
        logger: Logger to use
        reraise: Whether to reraise the exception
        default_return: Value to return if exception caught
    
    Example:
        @log_exceptions(reraise=False, default_return=None)
        def risky_operation():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Exception in {func.__name__}: {str(e)}",
                    extra={
                        "function": func.__name__,
                        "exception_type": type(e).__name__,
                        "exception_message": str(e)
                    },
                    exc_info=True
                )
                
                if reraise:
                    raise
                return default_return
        
        return wrapper
    return decorator


def log_entry_exit(
    logger: Optional[logging.Logger] = None,
    level: int = logging.DEBUG
):
    """
    Decorator to log function entry and exit
    
    Args:
        logger: Logger to use
        level: Log level
    
    Example:
        @log_entry_exit
        def important_function(data):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            logger.log(level, f"Entering {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"Exiting {func.__name__}")
                return result
            except Exception as e:
                logger.log(level, f"Exiting {func.__name__} with exception: {type(e).__name__}")
                raise
        
        return wrapper
    return decorator


def log_rate_limit(max_per_minute: int = 60):
    """
    Decorator to rate limit logging for high-frequency functions
    
    Args:
        max_per_minute: Maximum log calls per minute
    
    Example:
        @log_rate_limit(max_per_minute=10)
        def frequent_operation():
            logger.debug("This will be rate limited")
    """
    def decorator(func: Callable) -> Callable:
        last_log_time = [0.0]  # Mutable to track state
        log_count = [0]
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            
            # Reset counter every minute
            if current_time - last_log_time[0] >= 60:
                last_log_time[0] = current_time
                log_count[0] = 0
            
            # Check if we should log
            if log_count[0] < max_per_minute:
                log_count[0] += 1
                return func(*args, **kwargs)
            
            # Silently skip logging
            return None
        
        return wrapper
    return decorator


class LogContext:
    """
    Context manager for adding temporary log context
    
    Example:
        with LogContext(operation="batch_process", batch_id=123):
            # All log calls here will include operation and batch_id
            logger.info("Processing items")
    """
    
    def __init__(self, **context):
        self.context = context
        self.token = None
    
    def __enter__(self):
        # Store context in thread-local storage
        import threading
        if not hasattr(threading.current_thread(), 'log_context'):
            threading.current_thread().log_context = {}
        threading.current_thread().log_context.update(self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clear context
        import threading
        if hasattr(threading.current_thread(), 'log_context'):
            for key in self.context:
                threading.current_thread().log_context.pop(key, None)
