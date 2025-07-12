"""
Main orchestrator for the Communication Layer.

Manages all transport instances, coordinates system interactions,
and provides the high-level API for order processing.
"""

import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import structlog

from .transport import Transport, TransportConfig, TransportType, TransportFactory, RetryPolicy
from .logger import get_logger
from .transport_registry import register_all_transports, get_registered_transports

logger = get_logger(__name__)

class OrderStatus(Enum):
    """Order processing status."""
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class OrderItem:
    """Individual item in an order."""
    item_id: str
    name: str
    quantity: int
    components: List[str]

@dataclass
class Order:
    """Complete order information."""
    order_id: str
    customer_name: str
    items: List[OrderItem]
    estimated_time: Optional[int] = None
    serving_unit_count: Optional[int] = None
    status: OrderStatus = OrderStatus.RECEIVED

@dataclass
class OrderResponse:
    """Response to an order request."""
    order_id: str
    estimated_time: int
    serving_unit_count: int
    status: OrderStatus

class CommunicationManager:
    """
    Main orchestrator for the Communication Layer.
    
    Manages all transport instances and coordinates the flow
    of orders through the various systems.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the communication manager.
        
        Args:
            config: Complete configuration from config.yaml
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.transports: Dict[str, Transport] = {}
        self.active_orders: Dict[str, Order] = {}
        self.performance_config = config.get('performance', {})
        
        # Semaphore to limit concurrent orders
        self.order_semaphore = asyncio.Semaphore(
            self.performance_config.get('max_concurrent_orders', 10)
        )
    
    async def initialize(self) -> None:
        """
        Initialize all transport instances.
        
        Creates and initializes all configured transports.
        """
        self.logger.info("Initializing Communication Manager")
        
        # Ensure all transports are registered
        register_all_transports()
        
        # Log registered transports for debugging
        registered_transports = get_registered_transports()
        self.logger.info(f"Registered transports: {list(registered_transports.keys())}")
        
        # Create transport configurations
        transport_configs = self._create_transport_configs()
        
        # Initialize all transports
        for name, config in transport_configs.items():
            try:
                transport = TransportFactory.create(config)
                await transport.initialize()
                self.transports[name] = transport
                self.logger.info(f"Initialized transport: {name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize transport {name}: {e}")
                raise
        
        self.logger.info("Communication Manager initialized successfully")
    
    async def shutdown(self) -> None:
        """
        Shutdown all transport instances.
        
        Gracefully closes all connections and cleans up resources.
        """
        self.logger.info("Shutting down Communication Manager")
        
        shutdown_tasks = []
        for name, transport in self.transports.items():
            shutdown_tasks.append(self._shutdown_transport(name, transport))
        
        await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        self.logger.info("Communication Manager shutdown complete")
    
    async def _shutdown_transport(self, name: str, transport: Transport) -> None:
        """Shutdown a single transport."""
        try:
            await transport.shutdown()
            self.logger.info(f"Shutdown transport: {name}")
        except Exception as e:
            self.logger.error(f"Error shutting down transport {name}: {e}")
    
    def _create_transport_configs(self) -> Dict[str, TransportConfig]:
        """Create transport configurations from config."""
        configs = {}
        transports_config = self.config.get('transports', {})
        
        for name, transport_config in transports_config.items():
            transport_type = TransportType(transport_config['type'])
            retry_config = transport_config.get('retry_policy', {})
            
            retry_policy = RetryPolicy(
                max_attempts=retry_config.get('max_attempts', 3),
                backoff_factor=retry_config.get('backoff_factor', 2.0),
                initial_delay=retry_config.get('initial_delay', 1.0),
                timeout=retry_config.get('timeout')
            )
            
            configs[name] = TransportConfig(
                name=name,
                transport_type=transport_type,
                config=transport_config,
                retry_policy=retry_policy
            )
        
        return configs
    
    async def process_order(self, order_data: Dict[str, Any]) -> OrderResponse:
        """
        Process a new order through all systems.
        
        This is the main orchestration method that coordinates
        the flow of an order through all connected systems.
        
        Args:
            order_data: Order data from the ordering screen
            
        Returns:
            Order response with estimated time and serving unit count
            
        Raises:
            Exception: If order processing fails
        """
        async with self.order_semaphore:
            return await self._process_order_internal(order_data)
    
    async def _process_order_internal(self, order_data: Dict[str, Any]) -> OrderResponse:
        """Internal order processing logic."""
        order_id = order_data['order_id']
        self.logger.info(f"Processing order: {order_id}")
        
        try:
            # Create order object
            order = self._create_order_from_data(order_data)
            self.active_orders[order_id] = order
            
            # Step 1: Get customer information from database
            customer_name = await self._get_customer_name(order_id)
            order.customer_name = customer_name
            
            # Step 2: Check robot arm state
            robot_state = await self._check_robot_arm_state()
            if robot_state != "UP":
                raise Exception(f"Robot arm not ready: {robot_state}")
            
            # Step 3: Send work to robot arm
            await self._send_work_to_robot_arm(order)
            
            # Step 4: Open serving units
            serving_units = await self._open_serving_units(order)
            
            # Step 5: Update Android screen
            await self._update_android_screen(order, serving_units)
            
            # Step 6: Play completion sound
            await self._play_completion_sound()
            
            # Create response
            response = OrderResponse(
                order_id=order_id,
                estimated_time=self._calculate_estimated_time(order),
                serving_unit_count=len(serving_units),
                status=OrderStatus.COMPLETED
            )
            
            self.logger.info(f"Order {order_id} processed successfully")
            return response
            
        except Exception as e:
            self.logger.error(f"Order {order_id} processing failed: {e}")
            await self._handle_order_failure(order_id, str(e))
            raise
    
    def _create_order_from_data(self, order_data: Dict[str, Any]) -> Order:
        """Create Order object from request data."""
        items = [
            OrderItem(
                item_id=item['id'],
                name=item['name'],
                quantity=item['quantity'],
                components=item.get('components', [])
            )
            for item in order_data['items']
        ]
        
        return Order(
            order_id=order_data['order_id'],
            customer_name="",  # Will be filled from database
            items=items
        )
    
    async def _get_customer_name(self, order_id: str) -> str:
        """Get customer name from database."""
        # TODO: Implement database client call
        self.logger.info(f"Getting customer name for order: {order_id}")
        return "John Doe"  # Placeholder
    
    async def _check_robot_arm_state(self) -> str:
        """Check robot arm state."""
        # TODO: Implement robot arm client call
        self.logger.info("Checking robot arm state")
        return "UP"  # Placeholder
    
    async def _send_work_to_robot_arm(self, order: Order) -> None:
        """Send work payload to robot arm."""
        # TODO: Implement robot arm work request
        self.logger.info(f"Sending work to robot arm for order: {order.order_id}")
        await asyncio.sleep(0.1)  # Simulate work
    
    async def _open_serving_units(self, order: Order) -> List[str]:
        """Open serving units for the order."""
        # TODO: Implement serving unit client calls
        self.logger.info(f"Opening serving units for order: {order.order_id}")
        serving_units = [f"unit_{i}" for i in range(len(order.items))]
        return serving_units
    
    async def _update_android_screen(self, order: Order, serving_units: List[str]) -> None:
        """Update Android screen with customer and serving unit info."""
        # TODO: Implement Android screen client call
        self.logger.info(f"Updating Android screen for order: {order.order_id}")
    
    async def _play_completion_sound(self) -> None:
        """Play completion sound."""
        # TODO: Implement sound player call
        self.logger.info("Playing completion sound")
    
    def _calculate_estimated_time(self, order: Order) -> int:
        """Calculate estimated completion time."""
        # TODO: Implement time calculation logic
        base_time = 30  # seconds
        item_time = len(order.items) * 10
        return base_time + item_time
    
    async def _handle_order_failure(self, order_id: str, error: str) -> None:
        """Handle order processing failure."""
        # TODO: Send SMS notification
        self.logger.error(f"Order {order_id} failed: {error}")
        
        # Remove from active orders
        if order_id in self.active_orders:
            del self.active_orders[order_id]
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of all transports.
        
        Returns:
            Dictionary with health status of each transport
        """
        health_status = {}
        
        for name, transport in self.transports.items():
            try:
                is_healthy = await transport.is_healthy()
                health_status[name] = {
                    "healthy": is_healthy,
                    "type": transport.config.transport_type.value
                }
            except Exception as e:
                health_status[name] = {
                    "healthy": False,
                    "error": str(e),
                    "type": transport.config.transport_type.value
                }
        
        return health_status
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Dictionary with various metrics
        """
        return {
            "active_orders": len(self.active_orders),
            "transport_health": await self.get_health_status(),
            "performance": {
                "max_concurrent_orders": self.performance_config.get('max_concurrent_orders'),
                "order_timeout": self.performance_config.get('order_timeout')
            }
        } 