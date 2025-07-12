"""
Transport registry for the Communication Layer.

This module ensures all transport classes are properly imported and registered
with the TransportFactory when the application starts.
"""

from app.core.transport import TransportFactory, TransportType

# Import all transport implementations to ensure they register themselves
def register_all_transports():
    """
    Register all transport implementations with the factory.
    
    This function imports all transport modules, which triggers their
    TransportFactory.register() calls at module load time.
    """
    
    # ROS2 transports
    try:
        from app.ros2.robot_arm import ROS2RobotArmTransport
        from app.ros2.serving_unit import ROS2ServingUnitTransport
        from app.ros2.android_screen import ROS2AndroidScreenTransport
    except ImportError as e:
        print(f"Warning: Could not import ROS2 transports: {e}")
    
    # HTTP transports
    try:
        from app.db_client import DatabaseClient
    except ImportError as e:
        print(f"Warning: Could not import database client: {e}")
    
    # Local OS transports
    try:
        from app.sound_player import SoundPlayer
    except ImportError as e:
        print(f"Warning: Could not import sound player: {e}")
    
    # SMS transports
    try:
        from app.notifier import NotificationSystem
    except ImportError as e:
        print(f"Warning: Could not import notification system: {e}")

# Auto-register transports when this module is imported
register_all_transports()

def get_registered_transports():
    """
    Get a list of all registered transport types.
    
    Returns:
        Dictionary mapping transport types to their registered classes
    """
    return TransportFactory._transport_classes.copy()

def is_transport_registered(transport_type: TransportType) -> bool:
    """
    Check if a transport type is registered.
    
    Args:
        transport_type: Transport type to check
        
    Returns:
        True if registered, False otherwise
    """
    return transport_type in TransportFactory._transport_classes 