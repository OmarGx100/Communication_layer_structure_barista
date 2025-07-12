"""
Main application entry point for the Communication Layer.

Initializes the communication manager, sets up HTTP server,
and handles graceful shutdown.
"""

import asyncio
import signal
import sys
from typing import Any, Dict
import yaml
import uvicorn

from .core.logger import setup_logging, get_logger
from .core.transport_registry import register_all_transports
from .core.manager import CommunicationManager
from .http.ordering import OrderingAPI

logger = get_logger(__name__)

class CommunicationLayerApp:
    """
    Main application class for the Communication Layer.
    
    Manages the complete lifecycle of the communication layer,
    including initialization, HTTP server, and graceful shutdown.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the communication layer application.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = None
        self.manager = None
        self.http_server = None
        self.shutdown_event = asyncio.Event()
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        try:
            logger.info(f"Loading configuration from {self.config_path}")
            
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            logger.info("Configuration loaded successfully")
            return config
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid configuration file: {e}")
            raise
    
    async def initialize(self) -> None:
        """
        Initialize the communication layer.
        
        Loads configuration, sets up logging, initializes
        communication manager, and creates HTTP server.
        """
        try:
            logger.info("Initializing Communication Layer")
            
            # Load configuration
            self.config = self.load_config()
            
            # Setup logging
            setup_logging(self.config)
            logger.info("Logging configured")
            
            # Initialize communication manager
            self.manager = CommunicationManager(self.config)
            await self.manager.initialize()
            logger.info("Communication manager initialized")
            
            # Create HTTP server
            http_config = self.config.get('http_server', {})
            self.http_server = OrderingAPI(self.manager, http_config)
            logger.info("HTTP server created")
            
            logger.info("Communication Layer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Communication Layer: {e}")
            raise
    
    async def run(self) -> None:
        """
        Run the communication layer.
        
        Starts the HTTP server and waits for shutdown signal.
        """
        try:
            logger.info("Starting Communication Layer")
            
            # Get HTTP server configuration
            http_config = self.config.get('http_server', {})
            host = http_config.get('host', '0.0.0.0')
            port = http_config.get('port', 8000)
            
            # Create uvicorn config
            uvicorn_config = uvicorn.Config(
                app=self.http_server.get_app(),
                host=host,
                port=port,
                log_level="info",
                access_log=True
            )
            
            # Start server
            server = uvicorn.Server(uvicorn_config)
            
            # Run server in background
            server_task = asyncio.create_task(server.serve())
            
            logger.info(f"HTTP server started on {host}:{port}")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            logger.info("Shutdown signal received, stopping server")
            
            # Stop server
            server.should_exit = True
            await server_task
            
        except Exception as e:
            logger.error(f"Error running Communication Layer: {e}")
            raise
    
    async def shutdown(self) -> None:
        """
        Shutdown the communication layer.
        
        Gracefully shuts down all components and cleanup resources.
        """
        try:
            logger.info("Shutting down Communication Layer")
            
            # Shutdown communication manager
            if self.manager:
                await self.manager.shutdown()
                logger.info("Communication manager shutdown complete")
            
            logger.info("Communication Layer shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

async def main():
    """
    Main entry point for the Communication Layer.
    
    Creates and runs the application with proper error handling
    and graceful shutdown.
    """
    app = None
    
    try:
        # Create application
        app = CommunicationLayerApp()
        
        # Initialize
        await app.initialize()
        
        # Run
        await app.run()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        # Shutdown
        if app:
            await app.shutdown()

def run():
    """
    Run the Communication Layer application.
    
    Entry point for command-line execution.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run() 