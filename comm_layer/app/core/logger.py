"""
Structured logging configuration for the Communication Layer.

Provides JSON-formatted logging with correlation IDs and timestamps
for observability across all system interactions.
"""

import json
import sys
import uuid
from typing import Any, Dict, Optional
from contextvars import ContextVar
import structlog
from structlog.stdlib import LoggerFactory

# Correlation ID context variable for request tracing
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

def get_correlation_id() -> str:
    """Get or generate a correlation ID for the current request."""
    current_id = correlation_id.get()
    if current_id is None:
        current_id = str(uuid.uuid4())
        correlation_id.set(current_id)
    return current_id

def setup_logging(config: Dict[str, Any]) -> None:
    """
    Configure structured logging based on configuration.
    
    Args:
        config: Logging configuration from config.yaml
    """
    log_config = config.get('logging', {})
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            _add_correlation_id,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def _add_correlation_id(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add correlation ID to log entries."""
    event_dict['correlation_id'] = get_correlation_id()
    return event_dict

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structured logger
    """
    return structlog.get_logger(name)

# Global logger instance
logger = get_logger(__name__) 