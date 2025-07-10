"""
Notification system for the Communication Layer.

Provides abstract SMS interface for sending failure alerts
and system notifications.
"""

import asyncio
from typing import Any, Dict, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .core.transport import Transport, TransportConfig, TransportType, TransportError
from .core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class NotificationMessage:
    """Notification message structure."""
    recipient: str
    subject: str
    body: str
    priority: str = "normal"  # "low", "normal", "high", "urgent"

@dataclass
class SMSMessage:
    """SMS message structure."""
    recipient: str
    message: str
    priority: str = "normal"

class SMSProvider(ABC):
    """
    Abstract SMS provider interface.
    
    Defines the contract for SMS providers without
    concrete implementation.
    """
    
    @abstractmethod
    async def send_sms(self, message: SMSMessage) -> bool:
        """
        Send SMS message.
        
        Args:
            message: SMS message to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if SMS provider is available.
        
        Returns:
            True if provider is available, False otherwise
        """
        pass

class MockSMSProvider(SMSProvider):
    """
    Mock SMS provider for testing and development.
    
    Simulates SMS sending without actual provider integration.
    """
    
    def __init__(self):
        self.sent_messages = []
        self.available = True
    
    async def send_sms(self, message: SMSMessage) -> bool:
        """Mock SMS sending."""
        self.sent_messages.append(message)
        logger.info(f"Mock SMS sent to {message.recipient}: {message.message}")
        return True
    
    async def is_available(self) -> bool:
        """Check mock provider availability."""
        return self.available
    
    def get_sent_messages(self) -> List[SMSMessage]:
        """Get list of sent messages for testing."""
        return self.sent_messages.copy()

class NotificationSystem(Transport):
    """
    Notification system transport.
    
    Handles SMS notifications for system failures and alerts
    using abstract SMS provider interface.
    """
    
    def __init__(self, config: TransportConfig):
        """
        Initialize notification system.
        
        Args:
            config: Transport configuration
        """
        super().__init__(config)
        self.logger = get_logger(f"{__name__}.{config.name}")
        
        # SMS provider
        self.sms_provider = None
        
        # Extract configuration
        self.provider_type = config.config.get('provider', 'abstract')
        self.recipients = config.config.get('recipients', [])
        self.templates = config.config.get('templates', {})
    
    async def initialize(self) -> None:
        """
        Initialize notification system.
        
        Creates SMS provider based on configuration.
        """
        try:
            self.logger.info("Initializing notification system")
            
            # Create SMS provider
            if self.provider_type == 'abstract':
                self.sms_provider = MockSMSProvider()
            else:
                # TODO: Create concrete SMS provider based on type
                self.sms_provider = MockSMSProvider()
            
            self.logger.info("Notification system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize notification system: {e}")
            raise TransportError(f"Notification system initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """
        Shutdown notification system.
        
        Cleanup SMS provider resources.
        """
        try:
            self.logger.info("Shutting down notification system")
            
            # TODO: Cleanup SMS provider if needed
            self.sms_provider = None
            
            self.logger.info("Notification system shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during notification system shutdown: {e}")
    
    async def is_healthy(self) -> bool:
        """
        Check if notification system is healthy.
        
        Returns:
            True if SMS provider is available
        """
        try:
            if not self.sms_provider:
                return False
            
            return await self.sms_provider.is_available()
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def send_failure_alert(self, system: str, error: str, order_id: Optional[str] = None) -> None:
        """
        Send failure alert SMS.
        
        Args:
            system: System that failed (e.g., 'robot_arm', 'serving_unit')
            error: Error description
            order_id: Optional order ID associated with failure
            
        Raises:
            TransportError: If SMS sending fails
        """
        try:
            self.logger.info(f"Sending failure alert for {system}: {error}")
            
            # Create SMS message
            message = self._create_failure_message(system, error, order_id)
            
            # Send to all recipients
            for recipient in self.recipients:
                sms_message = SMSMessage(
                    recipient=recipient,
                    message=message,
                    priority="high"
                )
                
                success = await self.sms_provider.send_sms(sms_message)
                if not success:
                    self.logger.error(f"Failed to send SMS to {recipient}")
            
        except Exception as e:
            self.logger.error(f"Failed to send failure alert: {e}")
            raise TransportError(f"Failure alert sending failed: {e}")
    
    async def send_system_alert(self, subject: str, message: str, priority: str = "normal") -> None:
        """
        Send general system alert SMS.
        
        Args:
            subject: Alert subject
            message: Alert message
            priority: Message priority
            
        Raises:
            TransportError: If SMS sending fails
        """
        try:
            self.logger.info(f"Sending system alert: {subject}")
            
            # Create SMS message
            sms_text = f"{subject}: {message}"
            
            # Send to all recipients
            for recipient in self.recipients:
                sms_message = SMSMessage(
                    recipient=recipient,
                    message=sms_text,
                    priority=priority
                )
                
                success = await self.sms_provider.send_sms(sms_message)
                if not success:
                    self.logger.error(f"Failed to send SMS to {recipient}")
            
        except Exception as e:
            self.logger.error(f"Failed to send system alert: {e}")
            raise TransportError(f"System alert sending failed: {e}")
    
    async def send_component_alert(self, component: str, level: str, message: str) -> None:
        """
        Send component alert SMS.
        
        Args:
            component: Component name (e.g., 'milk', 'coffee', 'ice')
            level: Alert level ('warning', 'critical', 'empty')
            message: Alert message
            
        Raises:
            TransportError: If SMS sending fails
        """
        try:
            self.logger.info(f"Sending component alert: {component} - {level}")
            
            # Create SMS message
            sms_text = f"Component Alert - {component.upper()}: {message}"
            priority = "high" if level in ["critical", "empty"] else "normal"
            
            # Send to all recipients
            for recipient in self.recipients:
                sms_message = SMSMessage(
                    recipient=recipient,
                    message=sms_text,
                    priority=priority
                )
                
                success = await self.sms_provider.send_sms(sms_message)
                if not success:
                    self.logger.error(f"Failed to send SMS to {recipient}")
            
        except Exception as e:
            self.logger.error(f"Failed to send component alert: {e}")
            raise TransportError(f"Component alert sending failed: {e}")
    
    def _create_failure_message(self, system: str, error: str, order_id: Optional[str] = None) -> str:
        """
        Create failure alert message.
        
        Args:
            system: System that failed
            error: Error description
            order_id: Optional order ID
            
        Returns:
            Formatted failure message
        """
        base_message = f"SYSTEM FAILURE: {system.upper()} - {error}"
        
        if order_id:
            base_message += f" (Order: {order_id})"
        
        return base_message
    
    def add_recipient(self, recipient: str) -> None:
        """
        Add SMS recipient.
        
        Args:
            recipient: Phone number to add
        """
        if recipient not in self.recipients:
            self.recipients.append(recipient)
            self.logger.info(f"Added SMS recipient: {recipient}")
    
    def remove_recipient(self, recipient: str) -> None:
        """
        Remove SMS recipient.
        
        Args:
            recipient: Phone number to remove
        """
        if recipient in self.recipients:
            self.recipients.remove(recipient)
            self.logger.info(f"Removed SMS recipient: {recipient}")

# Register with transport factory
TransportFactory.register(TransportType.SMS, NotificationSystem) 