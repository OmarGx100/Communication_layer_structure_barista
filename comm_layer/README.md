# Communication Layer

A high-performance, extensible communication layer for multi-system integration in a food service automation environment.

## Overview

This communication layer orchestrates interactions between:
- Ordering Screens (HTTP/FastAPI)
- Robot Arm (ROS2)
- Database Service (HTTP/FastAPI)
- Sound System (Local OS)
- Serving Units (ROS2)
- Android Screen (ROS2)
- Notification System (SMS)

## Architecture

- **Async-first**: Built on asyncio for high concurrency and low latency
- **Transport-agnostic**: Abstract transport layer supporting HTTP, ROS2, and local OS calls
- **Configuration-driven**: All endpoints and policies defined in YAML
- **Extensible**: Easy to add new transports without code changes
- **Observable**: Structured JSON logging throughout

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure endpoints in `config.yaml`

3. Run the service:
```bash
python -m app.main
```

## Configuration

All system endpoints, retry policies, and security settings are defined in `config.yaml`. See the configuration section for details.

## API Documentation

- **Ordering API**: `POST /order` - Submit new orders
- **Health Check**: `GET /health` - Service status
- **Metrics**: `GET /metrics` - Performance metrics

## Development

The codebase follows a modular architecture:
- `app/core/` - Abstract transport layer and orchestration
- `app/http/` - HTTP/FastAPI endpoints
- `app/ros2/` - ROS2 client implementations
- `app/` - System-specific clients (DB, Sound, Notifications) 