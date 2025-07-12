# Quick Start Guide

This guide will help you get the Communication Layer up and running quickly.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd comm_layer
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation:**
   ```bash
   python -c "import fastapi, rclpy, structlog; print('Dependencies installed successfully!')"
   ```

4. **Test transport registration:**
   ```bash
   python test_transport_registration.py
   ```

## Configuration

The system is pre-configured with a `config.yaml` file that includes:

- **API Keys**: `order-screen-1-key` and `order-screen-2-key`
- **HTTP Server**: Running on `0.0.0.0:8000`
- **Transport endpoints**: All configured for local development
- **Retry policies**: Optimized for reliability

## Running the Communication Layer

### Start the Server

```bash
# From the comm_layer directory
python -m app.main
```

You should see output like:
```
INFO     Loading configuration from config.yaml
INFO     Logging configured
INFO     Initializing Communication Manager
INFO     Initialized transport: robot_arm
INFO     Initialized transport: serving_units
INFO     Initialized transport: android_screen
INFO     Initialized transport: database
INFO     Initialized transport: sound_system
INFO     Initialized transport: notifications
INFO     Communication manager initialized
INFO     HTTP server created
INFO     Communication Layer initialized successfully
INFO     Starting Communication Layer
INFO     HTTP server started on 0.0.0.0:8000
```

### Verify the Server is Running

Open a new terminal and test the health endpoint:

```bash
curl http://localhost:8000/health
```

You should see a JSON response with system status.

## Testing the System

### Run the Test Suite

```bash
# In a new terminal
python test_order_flow.py
```

This will run comprehensive tests including:
- Health check
- Order submission
- Concurrent order processing
- System metrics

### Manual Testing

#### 1. Submit an Order

```bash
curl -X POST http://localhost:8000/order \
  -H "Content-Type: application/json" \
  -H "X-API-Key: order-screen-1-key" \
  -d '{
    "order_id": "test_order_001",
    "items": [
      {
        "id": "coffee_001",
        "name": "Espresso",
        "quantity": 1,
        "components": ["coffee", "water"]
      }
    ]
  }'
```

Expected response:
```json
{
  "order_id": "test_order_001",
  "estimated_time": 40,
  "serving_unit_count": 1,
  "status": "completed"
}
```

#### 2. Check System Metrics

```bash
curl http://localhost:8000/metrics
```

#### 3. Test API Key Authentication

```bash
# This should fail
curl -X POST http://localhost:8000/order \
  -H "Content-Type: application/json" \
  -H "X-API-Key: invalid-key" \
  -d '{"order_id": "test", "items": []}'
```

## API Documentation

Once the server is running, you can access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## System Architecture Overview

The Communication Layer orchestrates interactions between:

1. **Ordering Screens** (HTTP) → Receive orders
2. **Database Service** (HTTP) → Customer lookup, menu operations
3. **Robot Arm** (ROS2) → State checking, work execution
4. **Serving Units** (ROS2) → Opening units for orders
5. **Android Screen** (ROS2) → Display customer and serving info
6. **Sound System** (Local OS) → Audio notifications
7. **Notification System** (SMS) → Failure alerts

## Order Flow Example

1. **Order Received**: HTTP POST to `/order`
2. **Customer Lookup**: Database query for customer name
3. **Robot Arm Check**: Verify arm is in "UP" state
4. **Work Execution**: Send work payload to robot arm
5. **Serving Units**: Open appropriate serving units
6. **Android Update**: Send customer and unit info to screen
7. **Sound Playback**: Play completion sound
8. **Response**: Return estimated time and unit count

## Troubleshooting

### Common Issues

1. **Port already in use**:
   ```bash
   # Change port in config.yaml
   http_server:
     port: 8001
   ```

2. **Missing dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **ROS2 not available**:
   - The system includes mock implementations for development
   - Real ROS2 integration requires ROS2 environment setup

### Logs

The system uses structured JSON logging. Look for:
- `INFO` messages for normal operation
- `WARNING` messages for retries
- `ERROR` messages for failures

### Health Checks

Monitor system health:
```bash
curl http://localhost:8000/health | jq
```

## Development

### Transport Registration System

The Communication Layer uses a factory pattern for transport creation. All transport classes must register themselves with the `TransportFactory`:

1. **Automatic Registration**: Transport classes call `TransportFactory.register()` at module load time
2. **Registry Module**: `app/core/transport_registry.py` ensures all transports are imported and registered
3. **Factory Creation**: `TransportFactory.create()` creates instances based on configuration

### Adding New Transports

1. Create transport class inheriting from `Transport`
2. Implement required methods: `initialize()`, `shutdown()`, `is_healthy()`
3. Add `TransportFactory.register(TransportType.YOUR_TYPE, YourTransportClass)` at module level
4. Add import to `app/core/transport_registry.py`
5. Add configuration to `config.yaml`

### Extending the API

1. Add new endpoints in `app/http/ordering.py`
2. Update Pydantic models for request/response validation
3. Add corresponding logic in `app/core/manager.py`

### Configuration

All system behavior is controlled by `config.yaml`:
- Transport endpoints and retry policies
- Security settings (API keys)
- Performance limits
- Logging configuration

## Next Steps

1. **Integration**: Connect to real ROS2 systems
2. **SMS Provider**: Implement concrete SMS provider
3. **Monitoring**: Add metrics collection and alerting
4. **Scaling**: Configure for production deployment
5. **Testing**: Add unit and integration tests

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify configuration in `config.yaml`
3. Test individual components using the health endpoints
4. Review the detailed pseudocode in `ORDER_FLOW_PSEUDOCODE.md` 