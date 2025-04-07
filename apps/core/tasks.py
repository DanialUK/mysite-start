"""
Base task module for implementing common task patterns, logging, and error handling.
"""
import logging
import functools
import traceback
from typing import Any, Callable, Dict, Optional, Type, Union
from celery import Task, shared_task
from django.conf import settings
from django.db import transaction, DatabaseError

logger = logging.getLogger(__name__)

class BaseTask(Task):
    """
    Base task class with enhanced error handling, retry policies, and logging.
    
    This class provides:
    - Automatic retry for specific exceptions
    - Database transaction management
    - Enhanced logging for all stages of task lifecycle
    - Hooks for custom cleanup on failure
    
    Use this class as a base for all celery tasks to ensure consistent behavior.
    """
    abstract = True
    
    # Default retry policy
    autoretry_for = (Exception,)  # Retry for all exceptions by default
    retry_kwargs = {'max_retries': 5}
    retry_backoff = True  # Use exponential backoff
    retry_backoff_max = 600  # Maximum retry delay in seconds (10 minutes)
    retry_jitter = True  # Add randomness to retry delays
    
    # List of specific exceptions that should never be retried
    non_retryable_exceptions = (
        NotImplementedError,
        ValueError,
        KeyError,
        AttributeError,
        ImportError,
        MemoryError,
    )
    
    def __call__(self, *args, **kwargs):
        """Override the task calling method to add logging and error handling"""
        try:
            logger.info(f"Task {self.name}[{self.request.id}] started with args={args}, kwargs={kwargs}")
            return super().__call__(*args, **kwargs)
        except Exception as exc:
            # Log exception details
            logger.error(
                f"Task {self.name}[{self.request.id}] failed: {str(exc)}",
                exc_info=True,
                extra={
                    'task_id': self.request.id,
                    'task_args': args,
                    'task_kwargs': kwargs,
                },
            )
            # Re-raise the exception to let Celery's retry mechanism handle it
            raise
        finally:
            # Always log task completion, even if it failed
            logger.info(f"Task {self.name}[{self.request.id}] completed")
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle successful task completion"""
        logger.info(f"Task {self.name}[{task_id}] succeeded with result: {retval}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure with custom logic"""
        logger.error(
            f"Task {self.name}[{task_id}] failed: {str(exc)}",
            exc_info=True,
            extra={
                'task_id': task_id,
                'traceback': einfo.traceback if einfo else None,
            },
        )
        # Call custom cleanup method if it exists
        self.cleanup_on_failure(task_id, args, kwargs)
    
    def cleanup_on_failure(self, task_id, args, kwargs):
        """
        Custom cleanup logic to run when a task fails.
        Override this method in subclasses for custom cleanup.
        """
        pass
    
    def should_retry(self, exc, *args, **kwargs):
        """
        Determine if the task should be retried based on the exception.
        
        Args:
            exc: The exception that caused the task to fail
            
        Returns:
            bool: True if the task should be retried, False otherwise
        """
        # Don't retry for specific exceptions
        if isinstance(exc, self.non_retryable_exceptions):
            logger.info(f"Not retrying task {self.name} for exception {exc.__class__.__name__}")
            return False
        
        # Check if we've reached max retries (using request context)
        retries = self.request.retries
        max_retries = self.retry_kwargs.get('max_retries', 3)
        
        if retries >= max_retries:
            logger.warning(
                f"Task {self.name}[{self.request.id}] reached maximum retries ({max_retries})"
            )
            return False
        
        # Log the retry attempt
        logger.info(
            f"Retrying task {self.name}[{self.request.id}] due to {exc.__class__.__name__}: {str(exc)}, "
            f"retry {retries + 1}/{max_retries}"
        )
        return True

def atomic_task(*args, **kwargs):
    """
    Decorator for creating shared tasks that run in a database transaction.
    
    This decorator ensures that the task either completes successfully or
    the database is rolled back to maintain consistency.
    
    Usage:
        @atomic_task
        def my_task(arg1, arg2):
            # Task code running in a transaction
            ...
    
    Args:
        base (Task, optional): Base task class to use
        
    Returns:
        Task: A shared task that runs in a database transaction
    """
    def decorator(func):
        @shared_task(*args, **kwargs)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with transaction.atomic():
                    return func(*args, **kwargs)
            except DatabaseError as e:
                logger.error(f"Database error in atomic task {func.__name__}: {str(e)}", exc_info=True)
                # Re-raise for retry
                raise
            except Exception as e:
                logger.error(f"Error in atomic task {func.__name__}: {str(e)}", exc_info=True)
                # Re-raise for retry
                raise
        return wrapper
    
    # Allow both @atomic_task and @atomic_task(...)
    if len(args) == 1 and callable(args[0]):
        return decorator(args[0])
    return decorator

def long_running_task(*args, **kwargs):
    """
    Decorator for creating tasks with extended timeouts for long-running operations.
    
    This decorator is for tasks that need more time than the default timeouts.
    
    Usage:
        @long_running_task
        def my_long_task(arg1, arg2):
            # Long task code
            ...
    
    Args:
        base (Task, optional): Base task class to use
        
    Returns:
        Task: A shared task with extended timeouts
    """
    # Override the default settings with long-running timeouts
    kwargs.setdefault('time_limit', 3600)  # 1 hour
    kwargs.setdefault('soft_time_limit', 3300)  # 55 minutes
    
    def decorator(func):
        @shared_task(*args, **kwargs)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"Starting long-running task {func.__name__}")
            result = func(*args, **kwargs)
            logger.info(f"Completed long-running task {func.__name__}")
            return result
        return wrapper
    
    # Allow both @long_running_task and @long_running_task(...)
    if len(args) == 1 and callable(args[0]):
        return decorator(args[0])
    return decorator 