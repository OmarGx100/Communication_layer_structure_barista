#!/usr/bin/env python3
"""
Test script for the Communication Layer order flow.

Demonstrates the complete order processing flow from HTTP request
through all connected systems and back to response.
"""

import asyncio
import json
import httpx
from typing import Dict, Any

async def test_order_flow():
    """
    Test the complete order flow through the Communication Layer.
    
    This function demonstrates how an order flows through the system:
    1. HTTP request to ordering endpoint
    2. Communication manager orchestrates the flow
    3. Database lookup for customer info
    4. Robot arm state check and work request
    5. Serving unit operations
    6. Android screen updates
    7. Sound playback
    8. Response back to ordering screen
    """
    
    # Test order data
    order_data = {
        "order_id": "test_order_001",
        "items": [
            {
                "id": "coffee_001",
                "name": "Espresso",
                "quantity": 1,
                "components": ["coffee", "water"]
            },
            {
                "id": "latte_001", 
                "name": "Cappuccino",
                "quantity": 2,
                "components": ["coffee", "milk", "foam"]
            }
        ]
    }
    
    print("🚀 Testing Communication Layer Order Flow")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1. Health Check")
    print("-" * 20)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ System Status: {health_data['status']}")
                print(f"📊 Active Orders: {health_data['active_orders']}")
                print(f"🔧 Transports: {len(health_data['transports'])}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 2: Submit Order
    print("\n2. Submit Order")
    print("-" * 20)
    try:
        async with httpx.AsyncClient() as client:
            headers = {"X-API-Key": "order-screen-1-key"}
            response = await client.post(
                "http://localhost:8000/order",
                json=order_data,
                headers=headers
            )
            
            if response.status_code == 200:
                order_response = response.json()
                print(f"✅ Order Submitted: {order_response['order_id']}")
                print(f"⏱️  Estimated Time: {order_response['estimated_time']} seconds")
                print(f"📦 Serving Units: {order_response['serving_unit_count']}")
                print(f"📋 Status: {order_response['status']}")
            else:
                print(f"❌ Order submission failed: {response.status_code}")
                print(f"Error: {response.text}")
    except Exception as e:
        print(f"❌ Order submission error: {e}")
    
    # Test 3: Metrics
    print("\n3. System Metrics")
    print("-" * 20)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/metrics")
            if response.status_code == 200:
                metrics = response.json()
                print(f"📊 Active Orders: {metrics['active_orders']}")
                print(f"🔧 Transport Health: {len(metrics['transport_health'])} transports")
                print(f"⚡ Performance: {metrics['performance']}")
            else:
                print(f"❌ Metrics failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Metrics error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Order Flow Test Complete!")

async def test_concurrent_orders():
    """
    Test concurrent order processing.
    
    Demonstrates the system's ability to handle multiple
    simultaneous orders with proper concurrency control.
    """
    
    print("\n🔄 Testing Concurrent Orders")
    print("=" * 50)
    
    # Create multiple test orders
    orders = []
    for i in range(3):
        order_data = {
            "order_id": f"concurrent_order_{i+1:03d}",
            "items": [
                {
                    "id": f"item_{i+1}",
                    "name": f"Test Item {i+1}",
                    "quantity": 1,
                    "components": ["component_1", "component_2"]
                }
            ]
        }
        orders.append(order_data)
    
    async def submit_order(order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a single order and return the result."""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"X-API-Key": "order-screen-1-key"}
                response = await client.post(
                    "http://localhost:8000/order",
                    json=order_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Submit orders concurrently
    print(f"📤 Submitting {len(orders)} orders concurrently...")
    start_time = asyncio.get_event_loop().time()
    
    tasks = [submit_order(order) for order in orders]
    results = await asyncio.gather(*tasks)
    
    end_time = asyncio.get_event_loop().time()
    total_time = end_time - start_time
    
    # Process results
    successful_orders = 0
    for i, result in enumerate(results):
        if result["success"]:
            successful_orders += 1
            print(f"✅ Order {i+1}: {result['data']['order_id']} - {result['data']['estimated_time']}s")
        else:
            print(f"❌ Order {i+1}: Failed - {result['error']}")
    
    print(f"\n📊 Concurrent Test Results:")
    print(f"   Total Orders: {len(orders)}")
    print(f"   Successful: {successful_orders}")
    print(f"   Failed: {len(orders) - successful_orders}")
    print(f"   Total Time: {total_time:.2f} seconds")
    print(f"   Average Time: {total_time/len(orders):.2f} seconds per order")

async def main():
    """
    Main test function.
    
    Runs all tests in sequence.
    """
    print("🧪 Communication Layer Test Suite")
    print("=" * 60)
    
    # Wait a moment for the server to be ready
    print("⏳ Waiting for server to be ready...")
    await asyncio.sleep(2)
    
    # Run tests
    await test_order_flow()
    await test_concurrent_orders()
    
    print("\n🎯 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 