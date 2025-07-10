"""
HTTP endpoints for ordering screens.

Provides FastAPI endpoints for receiving orders from ordering screens
with API key authentication and concurrent request handling.
"""

from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
import structlog

from ..core.logger import get_logger
from ..core.manager import CommunicationManager, OrderResponse

logger = get_logger(__name__)

# Pydantic models for request/response validation
class OrderItem(BaseModel):
    """Individual item in an order request."""
    id: str = Field(..., description="Unique item identifier")
    name: str = Field(..., description="Item name")
    quantity: int = Field(..., gt=0, description="Quantity ordered")
    components: List[str] = Field(default=[], description="Required components")

class OrderRequest(BaseModel):
    """Complete order request from ordering screen."""
    order_id: str = Field(..., description="Unique order identifier")
    items: List[OrderItem] = Field(..., min_items=1, description="Ordered items")

class OrderResponseModel(BaseModel):
    """Response to an order request."""
    order_id: str
    estimated_time: int = Field(..., description="Estimated completion time in seconds")
    serving_unit_count: int = Field(..., description="Number of serving units used")
    status: str = Field(..., description="Order processing status")

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    transports: Dict[str, Dict[str, Any]]
    active_orders: int

class MetricsResponse(BaseModel):
    """Metrics response."""
    active_orders: int
    transport_health: Dict[str, Dict[str, Any]]
    performance: Dict[str, Any]

# API Key validation
async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """
    Verify API key from request header.
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    # TODO: Get valid API keys from configuration
    valid_keys = ["order-screen-1-key", "order-screen-2-key"]
    
    if x_api_key not in valid_keys:
        logger.warning(f"Invalid API key attempted: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    logger.info(f"Valid API key used: {x_api_key[:8]}...")
    return x_api_key

class OrderingAPI:
    """
    FastAPI application for ordering screen endpoints.
    
    Provides HTTP endpoints for order processing with authentication,
    concurrent request handling, and integration with the communication manager.
    """
    
    def __init__(self, manager: CommunicationManager, config: Dict[str, Any]):
        """
        Initialize the ordering API.
        
        Args:
            manager: Communication manager instance
            config: HTTP server configuration
        """
        self.manager = manager
        self.config = config
        self.logger = get_logger(__name__)
        
        # Create FastAPI app
        self.app = FastAPI(
            title="Communication Layer - Ordering API",
            description="HTTP endpoints for ordering screen integration",
            version="1.0.0"
        )
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""
        
        @self.app.post(
            "/order",
            response_model=OrderResponseModel,
            summary="Submit a new order",
            description="Process a new order through all connected systems"
        )
        async def submit_order(
            order_request: OrderRequest,
            api_key: str = Depends(verify_api_key)
        ) -> OrderResponseModel:
            """
            Submit a new order for processing.
            
            This endpoint receives orders from ordering screens and
            orchestrates the complete order processing flow through
            all connected systems (robot arm, serving units, etc.).
            
            Args:
                order_request: Order details from the ordering screen
                api_key: Validated API key
                
            Returns:
                Order response with estimated time and serving unit count
                
            Raises:
                HTTPException: If order processing fails
            """
            try:
                self.logger.info(
                    f"Received order request",
                    order_id=order_request.order_id,
                    item_count=len(order_request.items),
                    api_key=api_key[:8] + "..."
                )
                
                # Convert to dict for manager
                order_data = order_request.dict()
                
                # Process order through communication manager
                response = await self.manager.process_order(order_data)
                
                # Convert to response model
                return OrderResponseModel(
                    order_id=response.order_id,
                    estimated_time=response.estimated_time,
                    serving_unit_count=response.serving_unit_count,
                    status=response.status.value
                )
                
            except Exception as e:
                self.logger.error(
                    f"Order processing failed",
                    order_id=order_request.order_id,
                    error=str(e)
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Order processing failed: {str(e)}"
                )
        
        @self.app.get(
            "/health",
            response_model=HealthResponse,
            summary="Health check",
            description="Check the health status of all transports"
        )
        async def health_check() -> HealthResponse:
            """
            Check the health status of the communication layer.
            
            Returns:
                Health status of all transports and active orders
            """
            try:
                transport_health = await self.manager.get_health_status()
                metrics = await self.manager.get_metrics()
                
                return HealthResponse(
                    status="healthy" if all(t.get("healthy", False) for t in transport_health.values()) else "degraded",
                    transports=transport_health,
                    active_orders=metrics["active_orders"]
                )
                
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Health check failed: {str(e)}"
                )
        
        @self.app.get(
            "/metrics",
            response_model=MetricsResponse,
            summary="Performance metrics",
            description="Get detailed performance metrics"
        )
        async def get_metrics() -> MetricsResponse:
            """
            Get detailed performance metrics.
            
            Returns:
                Performance metrics including active orders and transport health
            """
            try:
                metrics = await self.manager.get_metrics()
                
                return MetricsResponse(
                    active_orders=metrics["active_orders"],
                    transport_health=metrics["transport_health"],
                    performance=metrics["performance"]
                )
                
            except Exception as e:
                self.logger.error(f"Metrics retrieval failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Metrics retrieval failed: {str(e)}"
                )
        
        @self.app.get(
            "/",
            summary="API information",
            description="Get API information and available endpoints"
        )
        async def root() -> Dict[str, Any]:
            """
            Get API information.
            
            Returns:
                API information and available endpoints
            """
            return {
                "name": "Communication Layer - Ordering API",
                "version": "1.0.0",
                "endpoints": {
                    "submit_order": "POST /order",
                    "health_check": "GET /health",
                    "metrics": "GET /metrics"
                },
                "documentation": "/docs"
            }
    
    def get_app(self) -> FastAPI:
        """
        Get the FastAPI application instance.
        
        Returns:
            Configured FastAPI application
        """
        return self.app 