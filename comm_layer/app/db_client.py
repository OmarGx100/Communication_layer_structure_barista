"""
Database client for the Communication Layer.

Provides HTTP-based communication with the database service
for customer lookup and menu operations.
"""

import asyncio
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
import httpx

from .core.transport import Transport, TransportConfig, TransportType, TransportError, TransportFactory
from .core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class CustomerData:
    """Customer data from database."""
    order_id: str
    customer_name: str
    email: Optional[str] = None
    phone: Optional[str] = None

@dataclass
class MenuItem:
    """Menu item information."""
    item_id: str
    name: str
    components: List[str]
    available: bool = True

class DatabaseClient(Transport):
    """
    HTTP client for database service communication.
    
    Handles customer lookup and menu operations via HTTP
    requests to the database service.
    """
    
    def __init__(self, config: TransportConfig):
        """
        Initialize database client.
        
        Args:
            config: Transport configuration
        """
        super().__init__(config)
        self.logger = get_logger(f"{__name__}.{config.name}")
        
        # HTTP client
        self.http_client = None
        
        # Extract configuration
        self.base_url = config.config.get('base_url', 'http://database-service:8080')
        self.endpoints = config.config.get('endpoints', {})
    
    async def initialize(self) -> None:
        """
        Initialize HTTP client.
        
        Creates httpx client for database service communication.
        """
        try:
            self.logger.info("Initializing database client")
            
            # Create HTTP client with timeout
            timeout = self.config.retry_policy.timeout or 5.0
            self.http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            
            self.logger.info("Database client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database client: {e}")
            raise TransportError(f"Database client initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """
        Shutdown HTTP client.
        
        Closes httpx client and cleanup resources.
        """
        try:
            self.logger.info("Shutting down database client")
            
            if self.http_client:
                await self.http_client.aclose()
            
            self.logger.info("Database client shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during database client shutdown: {e}")
    
    async def is_healthy(self) -> bool:
        """
        Check if database client is healthy.
        
        Returns:
            True if HTTP client is available and database is reachable
        """
        try:
            if not self.http_client:
                return False
            
            # TODO: Implement health check endpoint
            # response = await self.http_client.get("/health")
            # return response.status_code == 200
            
            return True  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def get_customer(self, order_id: str) -> CustomerData:
        """
        Get customer information by order ID.
        
        Args:
            order_id: Order ID to lookup
            
        Returns:
            Customer data
            
        Raises:
            TransportError: If customer lookup fails
        """
        try:
            self.logger.info(f"Looking up customer for order: {order_id}")
            
            endpoint = self.endpoints.get('customer_lookup', '/customer/{order_id}')
            url = endpoint.format(order_id=order_id)
            
            # TODO: Make actual HTTP request
            # response = await self.http_client.get(url)
            # response.raise_for_status()
            # customer_data = response.json()
            
            # Simulate response
            await asyncio.sleep(0.1)
            customer_data = {
                "order_id": order_id,
                "customer_name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890"
            }
            
            customer = CustomerData(**customer_data)
            self.logger.info(f"Customer lookup successful: {customer.customer_name}")
            return customer
            
        except Exception as e:
            self.logger.error(f"Failed to lookup customer {order_id}: {e}")
            raise TransportError(f"Customer lookup failed: {e}")
    
    async def disable_menu_items(self, components: List[str]) -> List[str]:
        """
        Disable menu items that use specified components.
        
        Args:
            components: List of components that are empty/unavailable
            
        Returns:
            List of disabled menu item IDs
            
        Raises:
            TransportError: If menu disable operation fails
        """
        try:
            self.logger.info(f"Disabling menu items for components: {components}")
            
            endpoint = self.endpoints.get('menu_disable', '/menu/disable')
            
            # TODO: Make actual HTTP request
            # response = await self.http_client.post(
            #     endpoint,
            #     json={"components": components}
            # )
            # response.raise_for_status()
            # result = response.json()
            
            # Simulate response
            await asyncio.sleep(0.1)
            disabled_items = [f"item_{comp}" for comp in components]
            
            self.logger.info(f"Disabled menu items: {disabled_items}")
            return disabled_items
            
        except Exception as e:
            self.logger.error(f"Failed to disable menu items: {e}")
            raise TransportError(f"Menu disable operation failed: {e}")
    
    async def get_menu_items(self) -> List[MenuItem]:
        """
        Get all menu items.
        
        Returns:
            List of menu items
            
        Raises:
            TransportError: If menu retrieval fails
        """
        try:
            self.logger.info("Retrieving menu items")
            
            # TODO: Implement menu retrieval endpoint
            # response = await self.http_client.get("/menu/items")
            # response.raise_for_status()
            # items_data = response.json()
            
            # Simulate response
            await asyncio.sleep(0.1)
            items_data = [
                {
                    "item_id": "coffee_001",
                    "name": "Espresso",
                    "components": ["coffee", "water"],
                    "available": True
                },
                {
                    "item_id": "latte_001",
                    "name": "Cappuccino",
                    "components": ["coffee", "milk", "foam"],
                    "available": True
                }
            ]
            
            menu_items = [MenuItem(**item) for item in items_data]
            self.logger.info(f"Retrieved {len(menu_items)} menu items")
            return menu_items
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve menu items: {e}")
            raise TransportError(f"Menu retrieval failed: {e}")
    
    async def check_component_availability(self, components: List[str]) -> Dict[str, bool]:
        """
        Check availability of components.
        
        Args:
            components: List of components to check
            
        Returns:
            Dictionary mapping component names to availability status
            
        Raises:
            TransportError: If component check fails
        """
        try:
            self.logger.info(f"Checking component availability: {components}")
            
            # TODO: Implement component availability endpoint
            # response = await self.http_client.post(
            #     "/components/check",
            #     json={"components": components}
            # )
            # response.raise_for_status()
            # availability = response.json()
            
            # Simulate response
            await asyncio.sleep(0.1)
            availability = {comp: True for comp in components}
            
            self.logger.info(f"Component availability: {availability}")
            return availability
            
        except Exception as e:
            self.logger.error(f"Failed to check component availability: {e}")
            raise TransportError(f"Component availability check failed: {e}")

# Register with transport factory
TransportFactory.register(TransportType.HTTP_CLIENT, DatabaseClient) 