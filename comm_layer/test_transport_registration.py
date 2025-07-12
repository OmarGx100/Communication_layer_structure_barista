#!/usr/bin/env python3
"""
Test script to verify transport registration.

This script checks that all transport classes are properly registered
with the TransportFactory.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_transport_registration():
    """Test that all transport classes are properly registered."""
    
    print("🧪 Testing Transport Registration")
    print("=" * 50)
    
    try:
        # Import the transport registry to trigger registrations
        from app.core.transport_registry import register_all_transports, get_registered_transports
        from app.core.transport import TransportFactory, TransportType
        print(f"FFFFFFFFFFFFFFFFFFFFFFFF {type(TransportFactory)}")
        # Register all transports
        register_all_transports()
        
        # Get registered transports
        registered_transports = get_registered_transports()
        
        print(f"📋 Registered Transport Types: {len(registered_transports)}")
        print("-" * 30)
        
        for transport_type, transport_class in registered_transports.items():
            print(f"✅ {transport_type.value}: {transport_class.__name__}")
        
        # Test factory listing
        factory_transports = TransportFactory.list_registered_transports()
        print(f"\n🏭 Factory Registered Transports: {len(factory_transports)}")
        print("-" * 30)
        
        for transport_type, transport_class in factory_transports.items():
            print(f"✅ {transport_type.value}: {transport_class.__name__}")
        
        # Verify all expected transport types are registered
        expected_types = [
            TransportType.ROS2,
            TransportType.HTTP_CLIENT,
            TransportType.LOCAL_OS,
            TransportType.SMS
        ]
        
        print(f"\n🔍 Checking Expected Transport Types")
        print("-" * 30)
        
        missing_types = []
        for expected_type in expected_types:
            if expected_type in registered_transports:
                print(f"✅ {expected_type.value}: Registered")
            else:
                print(f"❌ {expected_type.value}: Missing")
                missing_types.append(expected_type)
        
        if missing_types:
            print(f"\n⚠️  Missing transport types: {[t.value for t in missing_types]}")
            return False
        else:
            print(f"\n🎉 All expected transport types are registered!")
            return True
            
    except Exception as e:
        print(f"❌ Error testing transport registration: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transport_creation():
    """Test creating transport instances."""
    
    print(f"\n🔧 Testing Transport Creation")
    print("=" * 50)
    
    try:
        from app.core.transport import TransportFactory, TransportType, TransportConfig, RetryPolicy
        
        # Test creating each transport type
        test_configs = [
            (TransportType.ROS2, "test_ros2"),
            (TransportType.HTTP_CLIENT, "test_http"),
            (TransportType.LOCAL_OS, "test_local"),
            (TransportType.SMS, "test_sms")
        ]
        
        for transport_type, name in test_configs:
            try:
                config = TransportConfig(
                    name=name,
                    transport_type=transport_type,
                    config={},
                    retry_policy=RetryPolicy()
                )
                
                transport = TransportFactory.create(config)
                print(f"✅ Created {transport_type.value}: {transport.__class__.__name__}")
                
            except Exception as e:
                print(f"❌ Failed to create {transport_type.value}: {e}")
                
    except Exception as e:
        print(f"❌ Error testing transport creation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Transport Registration Test Suite")
    print("=" * 60)
    
    # Test registration
    registration_success = test_transport_registration()
    
    if registration_success:
        # Test creation
        test_transport_creation()
    
    print(f"\n{'🎉 All tests passed!' if registration_success else '❌ Tests failed!'}") 