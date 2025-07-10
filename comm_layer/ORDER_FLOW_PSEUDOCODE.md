# Order Flow and Error Handling Pseudocode

This document provides detailed pseudocode for how orders flow through the Communication Layer and how failures and retries are handled.

## 1. HTTP Order Request Flow

```python
# 1. HTTP Request Received
POST /order
Headers: X-API-Key: "order-screen-1-key"
Body: {
    "order_id": "order_123",
    "items": [
        {"id": "coffee_001", "name": "Espresso", "quantity": 1, "components": ["coffee", "water"]},
        {"id": "latte_001", "name": "Cappuccino", "quantity": 2, "components": ["coffee", "milk", "foam"]}
    ]
}

# 2. API Key Validation
async def verify_api_key(x_api_key: str):
    valid_keys = ["order-screen-1-key", "order-screen-2-key"]
    if x_api_key not in valid_keys:
        raise HTTPException(401, "Invalid API key")
    return x_api_key

# 3. Order Processing Orchestration
async def process_order(order_data: Dict):
    # Acquire semaphore for concurrent order limit
    async with order_semaphore:
        return await _process_order_internal(order_data)

# 4. Internal Order Processing
async def _process_order_internal(order_data: Dict):
    order_id = order_data['order_id']
    
    try:
        # Step 1: Create order object
        order = create_order_from_data(order_data)
        active_orders[order_id] = order
        
        # Step 2: Get customer information (with retry)
        customer_name = await retry_with_policy(
            lambda: get_customer_name(order_id),
            max_attempts=3,
            backoff_factor=2.0
        )
        order.customer_name = customer_name
        
        # Step 3: Check robot arm state (with retry)
        robot_state = await retry_with_policy(
            lambda: check_robot_arm_state(),
            max_attempts=5,
            backoff_factor=1.5
        )
        
        if robot_state != "UP":
            raise Exception(f"Robot arm not ready: {robot_state}")
        
        # Step 4: Send work to robot arm (with retry)
        await retry_with_policy(
            lambda: send_work_to_robot_arm(order),
            max_attempts=5,
            backoff_factor=1.5
        )
        
        # Step 5: Open serving units (with retry)
        serving_units = await retry_with_policy(
            lambda: open_serving_units(order),
            max_attempts=3,
            backoff_factor=1.5
        )
        
        # Step 6: Update Android screen (with retry)
        await retry_with_policy(
            lambda: update_android_screen(order, serving_units),
            max_attempts=3,
            backoff_factor=1.5
        )
        
        # Step 7: Play completion sound (with retry)
        await retry_with_policy(
            lambda: play_completion_sound(),
            max_attempts=2,
            backoff_factor=1.0
        )
        
        # Step 8: Create response
        response = OrderResponse(
            order_id=order_id,
            estimated_time=calculate_estimated_time(order),
            serving_unit_count=len(serving_units),
            status=OrderStatus.COMPLETED
        )
        
        return response
        
    except Exception as e:
        # Handle order failure
        await handle_order_failure(order_id, str(e))
        raise
```

## 2. Database Client Operations

```python
# Customer Lookup with Retry
async def get_customer_name(order_id: str):
    endpoint = "/customer/{order_id}".format(order_id=order_id)
    
    async def _make_request():
        response = await http_client.get(endpoint)
        response.raise_for_status()
        customer_data = response.json()
        return customer_data['customer_name']
    
    return await retry_with_policy(
        _make_request,
        max_attempts=3,
        backoff_factor=2.0,
        timeout=5.0
    )

# Menu Disable Operation
async def disable_menu_items(components: List[str]):
    endpoint = "/menu/disable"
    
    async def _make_request():
        response = await http_client.post(
            endpoint,
            json={"components": components}
        )
        response.raise_for_status()
        return response.json()
    
    return await retry_with_policy(
        _make_request,
        max_attempts=3,
        backoff_factor=2.0,
        timeout=5.0
    )
```

## 3. ROS2 Robot Arm Communication

```python
# Robot Arm State Check
async def check_robot_arm_state():
    # Create future for state response
    state_future = asyncio.Future()
    state_callback = state_future.set_result
    
    # Publish state request
    state_msg = String()
    state_msg.data = "get_state"
    state_publisher.publish(state_msg)
    
    # Wait for response with timeout
    try:
        state_response = await asyncio.wait_for(state_future, timeout=10.0)
        return RobotArmState(state_response)
    except asyncio.TimeoutError:
        raise TransportError("Robot arm state request timed out")

# Robot Arm Work Request
async def send_work_to_robot_arm(order: Order):
    # Create futures for acknowledgment and completion
    ack_future = asyncio.Future()
    complete_future = asyncio.Future()
    
    work_ack_callback = lambda msg: ack_future.set_result(msg)
    work_complete_callback = lambda msg: complete_future.set_result(msg)
    
    # Store pending work
    pending_work[order.order_id] = {
        'ack_future': ack_future,
        'complete_future': complete_future,
        'payload': order
    }
    
    # Publish work request
    work_msg = String()
    work_msg.data = json.dumps(order.__dict__)
    work_publisher.publish(work_msg)
    
    # Wait for acknowledgment
    try:
        ack_response = await asyncio.wait_for(ack_future, timeout=10.0)
        logger.info(f"Work acknowledged: {order.order_id}")
        
        # Wait for completion
        complete_response = await asyncio.wait_for(complete_future, timeout=30.0)
        
        # Create work result
        result = WorkResult(
            order_id=order.order_id,
            success=True,
            completion_time=time.time(),
            details=complete_response
        )
        
        return result
        
    except asyncio.TimeoutError:
        raise TransportError(f"Work request timed out: {order.order_id}")
```

## 4. Serving Unit Operations

```python
# Open Single Serving Unit
async def open_serving_unit(unit_id: str):
    # Create service request
    request = String()
    request.data = unit_id
    
    # Call service
    future = open_service_client.call_async(request)
    
    # Wait for response with timeout
    try:
        response = await asyncio.wait_for(future, timeout=5.0)
        success = response.result().data == "success"
        
        if success:
            logger.info(f"Serving unit {unit_id} opened successfully")
        else:
            logger.warning(f"Failed to open serving unit {unit_id}")
        
        return success
        
    except asyncio.TimeoutError:
        raise TransportError(f"Serving unit open request timed out: {unit_id}")

# Open Multiple Serving Units Concurrently
async def open_multiple_units(unit_ids: List[str]):
    # Open units concurrently
    tasks = [open_serving_unit(unit_id) for unit_id in unit_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Create result dictionary
    result_dict = {}
    for unit_id, result in zip(unit_ids, results):
        if isinstance(result, Exception):
            logger.error(f"Failed to open unit {unit_id}: {result}")
            result_dict[unit_id] = False
        else:
            result_dict[unit_id] = result
    
    return result_dict
```

## 5. Android Screen Updates

```python
# Send Customer Information
async def send_customer_info(customer_info: CustomerInfo):
    # Create message
    msg = String()
    msg.data = json.dumps({
        "order_id": customer_info.order_id,
        "customer_name": customer_info.customer_name,
        "estimated_time": customer_info.estimated_time
    })
    
    # Publish message
    customer_info_publisher.publish(msg)
    logger.info(f"Customer info sent: {customer_info.order_id}")

# Send Serving Unit Information
async def send_serving_units(order_id: str, serving_units: List[ServingUnitInfo]):
    # Create message
    msg = String()
    msg.data = json.dumps({
        "order_id": order_id,
        "serving_units": [
            {
                "unit_id": unit.unit_id,
                "item_name": unit.item_name,
                "status": unit.status
            }
            for unit in serving_units
        ]
    })
    
    # Publish message
    serving_units_publisher.publish(msg)
    logger.info(f"Serving units sent: {order_id}")

# Complete Order Update
async def send_order_update(order_id: str, customer_info: CustomerInfo, serving_units: List[ServingUnitInfo]):
    # Send customer info and serving units concurrently
    await asyncio.gather(
        send_customer_info(customer_info),
        send_serving_units(order_id, serving_units)
    )
```

## 6. Sound System Operations

```python
# Play Sound File
async def play_sound_file(audio_file: str):
    # Stop any currently playing audio
    if current_process:
        await stop_current_audio()
    
    # Start new audio playback
    current_process = await asyncio.create_subprocess_exec(
        player_command, audio_file,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for playback to complete (non-blocking)
    asyncio.create_task(wait_for_playback_completion())

# Play Order Completion Sound
async def play_order_complete():
    audio_file = audio_files['order_complete']
    await play_sound_file(audio_file)

# Play Error Alert Sound
async def play_error_alert():
    audio_file = audio_files['error_alert']
    await play_sound_file(audio_file)
```

## 7. Notification System

```python
# Send Failure Alert
async def send_failure_alert(system: str, error: str, order_id: Optional[str] = None):
    # Create SMS message
    message = create_failure_message(system, error, order_id)
    
    # Send to all recipients
    for recipient in recipients:
        sms_message = SMSMessage(
            recipient=recipient,
            message=message,
            priority="high"
        )
        
        success = await sms_provider.send_sms(sms_message)
        if not success:
            logger.error(f"Failed to send SMS to {recipient}")

# Send Component Alert
async def send_component_alert(component: str, level: str, message: str):
    # Create SMS message
    sms_text = f"Component Alert - {component.upper()}: {message}"
    priority = "high" if level in ["critical", "empty"] else "normal"
    
    # Send to all recipients
    for recipient in recipients:
        sms_message = SMSMessage(
            recipient=recipient,
            message=sms_text,
            priority=priority
        )
        
        success = await sms_provider.send_sms(sms_message)
        if not success:
            logger.error(f"Failed to send SMS to {recipient}")
```

## 8. Retry Policy Implementation

```python
# Generic Retry Decorator
def retry_with_policy(func, max_attempts=3, backoff_factor=2.0, initial_delay=1.0, timeout=None):
    async def retry_wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                if timeout:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                else:
                    return await func(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                
                if attempt < max_attempts - 1:
                    # Calculate delay with exponential backoff
                    delay = initial_delay * (backoff_factor ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {max_attempts} attempts failed: {e}")
                    raise last_exception
        
        raise last_exception
    
    return retry_wrapper
```

## 9. Error Handling and Dead Letter Queue

```python
# Handle Order Failure
async def handle_order_failure(order_id: str, error: str):
    # Send SMS notification
    await notification_system.send_failure_alert(
        system="communication_layer",
        error=error,
        order_id=order_id
    )
    
    # Play error sound
    await sound_player.play_error_alert()
    
    # Remove from active orders
    if order_id in active_orders:
        del active_orders[order_id]
    
    # Send to dead letter queue if configured
    if dead_letter_queue_enabled:
        await send_to_dead_letter_queue(order_id, error)

# Dead Letter Queue
async def send_to_dead_letter_queue(order_id: str, error: str):
    dlq_message = {
        "order_id": order_id,
        "error": error,
        "timestamp": time.time(),
        "retry_count": 0
    }
    
    # TODO: Send to configured DLQ (file, database, or message queue)
    logger.error(f"Message sent to dead letter queue: {dlq_message}")

# Component Alert Handling
async def handle_component_alert(component: str, level: str, message: str):
    # Send SMS alert
    await notification_system.send_component_alert(component, level, message)
    
    # Disable menu items if component is empty
    if level == "empty":
        disabled_items = await database_client.disable_menu_items([component])
        logger.info(f"Disabled menu items for empty component {component}: {disabled_items}")
```

## 10. Health Check and Metrics

```python
# Health Check
async def get_health_status():
    health_status = {}
    
    for name, transport in transports.items():
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

# Metrics Collection
async def get_metrics():
    return {
        "active_orders": len(active_orders),
        "transport_health": await get_health_status(),
        "performance": {
            "max_concurrent_orders": performance_config.get('max_concurrent_orders'),
            "order_timeout": performance_config.get('order_timeout')
        }
    }
```

This pseudocode demonstrates the complete flow of an order through the Communication Layer, including all the retry logic, error handling, and integration points with the various systems. 