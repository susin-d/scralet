# Services Directory

This directory contains custom application services that power the Project Scarlet system.

## Camera Connectivity Features

The Project Scarlet system supports multiple camera types for comprehensive surveillance and person detection:

### Supported Camera Types

- **Bluetooth Cameras**: Wireless cameras that connect via Bluetooth for short-range surveillance
- **CCTV Network Cameras**: IP-based cameras supporting RTSP and HTTP streaming protocols

### Key Features

- **Automatic Discovery**: Scan for available cameras on the network or via Bluetooth
- **Connection Management**: Robust connection handling with automatic reconnection
- **Multi-Camera Support**: Simultaneously manage multiple cameras of different types
- **Real-time Monitoring**: Continuous health monitoring and status reporting
- **Security**: Encrypted connections and authentication support for network cameras

### Camera Services

- **edge-processor/**: Core camera processing service handling video streams, person detection, and face recognition
- **api-gateway/**: REST API service for camera management and configuration
- **face-recognition/**: Specialized service for advanced face detection and recognition
- **user-service/**: User management and authentication service
- **recommendation-service/**: Personalized content recommendation service
- **promotions-display-service/**: Dynamic promotions display service

## Service Architecture

Each service is containerized using Docker and communicates via REST APIs and message queues (Kafka). The edge-processor service acts as the central hub for camera connectivity and video processing.

## Getting Started

1. Configure your cameras using environment variables (see config/README.md)
2. Start the services using Docker Compose
3. Access camera feeds and management through the API Gateway

For detailed camera setup instructions, see the individual service README files.