"""
Abstract transport layer for the Communication Layer.

Defines the base interface for all transport types (HTTP, ROS2, Local OS, etc.)
and provides common functionality for retry policies and error handling.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from .logger import get_logger

logger = get_logger(__name__)

class TransportType(Enum):
    """Supported transport types."""
    HTTP_SERVER = "http_server"
    HTTP_CLIENT = "http_client"
    ROS2 = "ros2"
    LOCAL_OS = "local_os"
    SMS = "sms"

class TransportError(Exception):
    """Base exception for transport-related errors."""
    pass

class RetryableError(TransportError):
    """Error that should trigger retry logic."""
    pass

class FatalError(TransportError):
    """Error that should not be retried."""
    pass

@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0
    timeout: Optional[float] = None

@dataclass
class TransportConfig:
    """Configuration for a transport instance."""
    name: str
    transport_type: TransportType
    config: Dict[str, Any]
    retry_policy: RetryPolicy

class Transport(ABC):
    """
    Abstract base class for all transport implementations.
    
    Provides common functionality for retry logic, error handling,
    and configuration management.
    """
    
    def __init__(self, config: TransportConfig):
        """
        Initialize transport with configuration.
        
        Args:
            config: Transport configuration
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.{config.name}")
        self._setup_retry_decorator()
    
    def _setup_retry_decorator(self) -> None:
        """Setup retry decorator based on configuration."""
        policy = self.config.retry_policy
        
        self._retry_decorator = retry(
            stop=stop_after_attempt(policy.max_attempts),
            wait=wait_exponential(
                multiplier=policy.backoff_factor,
                min=policy.initial_delay
            ),
            retry_error_callback=self._handle_final_failure
        )
    
    async def _handle_final_failure(self, retry_state) -> None:
        """Handle final failure after all retries exhausted."""
        self.logger.error(
            "Transport operation failed after all retries",
            transport=self.config.name,
            attempts=retry_state.attempt_number,
            exception=str(retry_state.outcome.exception())
        )
        # TODO: Send to dead letter queue if configured
        raise retry_state.outcome.exception()
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the transport (connect, setup listeners, etc.).
        
        Must be called before using the transport.
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the transport (disconnect, cleanup, etc.).
        
        Should be called when the transport is no longer needed.
        """
        pass
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        """
        Check if the transport is healthy and ready for operations.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get transport-specific metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "transport_name": self.config.name,
            "transport_type": self.config.transport_type.value,
            "healthy": asyncio.create_task(self.is_healthy())
        }

class TransportFactory:
    """Factory for creating transport instances based on configuration."""
    
    _transport_classes: Dict[TransportType, type] = {}
    
    @classmethod
    def register(cls, transport_type: TransportType, transport_class: type) -> None:
        """
        Register a transport class for a specific type.
        
        Args:
            transport_type: Type of transport
            transport_class: Class implementing the transport
        """
        cls._transport_classes[transport_type] = transport_class
    
    @classmethod
    def create(cls, config: TransportConfig) -> Transport:
        """
        Create a transport instance based on configuration.
        
        Args:
            config: Transport configuration
            
        Returns:
            Configured transport instance
            
        Raises:
            ValueError: If transport type is not registered
        """
        transport_class = cls._transport_classes.get(config.transport_type)
        if not transport_class:
            available_types = list(cls._transport_classes.keys())
            raise ValueError(
                f"Unknown transport type: {config.transport_type}. "
                f"Available types: {available_types}"
            )
        
        return transport_class(config)
    
    @classmethod
    def list_registered_transports(cls) -> Dict[TransportType, type]:
        """
        Get all registered transport classes.
        
        Returns:
            Dictionary of registered transport types and their classes
        """
        return cls._transport_classes.copy() 