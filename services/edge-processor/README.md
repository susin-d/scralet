# Edge Processor Service

The Edge Processor service is the core component of Project Scarlet's camera connectivity system. It handles video stream processing, person detection, face recognition, and manages multiple camera types including Bluetooth and CCTV network cameras.

## Features

- **Multi-Camera Support**: Simultaneously manage Bluetooth and CCTV cameras
- **Real-time Video Processing**: Process video streams for person and face detection
- **Automatic Camera Discovery**: Scan networks and Bluetooth devices for available cameras
- **Connection Monitoring**: Continuous health monitoring with automatic reconnection
- **Event Streaming**: Send detection events to Kafka for downstream processing

## Supported Camera Types

### Bluetooth Cameras

Wireless cameras that connect via Bluetooth RFCOMM protocol for short-range surveillance.

**Features:**
- Automatic Bluetooth device discovery
- RFCOMM socket-based streaming
- JPEG frame transmission with size prefixing
- Connection retry with exponential backoff

### CCTV Network Cameras

IP-based cameras supporting RTSP and HTTP streaming protocols.

**Features:**
- RTSP/HTTP stream support
- Authentication (username/password)
- Network discovery via IP range scanning
- Multiple codec support via OpenCV

## Camera Setup and Configuration

### Bluetooth Camera Setup

1. **Discovery**: The service can automatically discover nearby Bluetooth cameras
2. **Pairing**: Ensure cameras are in pairing mode and discoverable
3. **Configuration**: Add camera details via environment variables or API

**Example Configuration:**
```json
{
  "id": "bluetooth_cam_1",
  "address": "AA:BB:CC:DD:EE:FF",
  "port": 1
}
```

### CCTV Camera Setup

1. **Network Configuration**: Ensure cameras are on the same network segment
2. **Port Configuration**: Verify RTSP (554) or HTTP ports are accessible
3. **Authentication**: Configure username/password if required
4. **Stream URL**: Verify camera stream URLs are correct

**Example Configuration:**
```json
{
  "id": "cctv_cam_1",
  "ip_address": "192.168.1.100",
  "port": 554,
  "protocol": "rtsp",
  "username": "admin",
  "password": "password123",
  "timeout": 10
}
```

## Camera Discovery Mechanisms

### Bluetooth Discovery

The service uses Python's `bluetooth` library to discover nearby devices:

```python
# Automatic discovery with configurable duration
devices = bluetooth.discover_devices(duration=8, lookup_names=True)
```

### Network Discovery

CCTV cameras are discovered by scanning IP ranges and testing common ports:

```python
# Scan IP range for open ports (554, 80, 8080)
discovered_cameras = CCTVCamera.discover_cameras("192.168.1.0/24", [554, 80, 8080])
```

## Environment Variables and Configuration

### Bluetooth Camera Configuration

- `BLUETOOTH_CAMERAS`: JSON string containing array of Bluetooth camera configurations
- `BLUETOOTH_DISCOVERY_DURATION`: Duration for Bluetooth device discovery (default: 8 seconds)

### CCTV Camera Configuration

- `CCTV_CAMERAS`: JSON string containing array of CCTV camera configurations
- `CCTV_DISCOVERY_IP_RANGE`: IP range for network discovery (default: "192.168.1.0/24")
- `CCTV_DISCOVERY_PORTS`: Comma-separated ports to scan (default: "554,80,8080")

### General Configuration

- `CAMERA_MONITOR_INTERVAL`: Interval for camera health monitoring (default: 10 seconds)
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka servers for event streaming
- `KAFKA_TOPIC`: Topic for camera sighting events

## Troubleshooting Common Camera Connection Issues

### Bluetooth Camera Issues

**Connection Failures:**
- Ensure camera is in pairing mode and discoverable
- Check Bluetooth adapter is enabled and functioning
- Verify camera address is correct
- Try increasing `BLUETOOTH_DISCOVERY_DURATION`

**Streaming Issues:**
- Check camera battery level
- Ensure line-of-sight connection
- Verify camera supports JPEG streaming
- Check for Bluetooth interference

### CCTV Camera Issues

**Connection Timeouts:**
- Verify IP address and port accessibility
- Check firewall settings allow camera ports
- Ensure camera is powered on and network-connected
- Try different timeout values

**Authentication Failures:**
- Verify username/password credentials
- Check if camera requires digest authentication
- Ensure credentials have streaming permissions

**Stream Format Issues:**
- Verify camera supports RTSP/HTTP streaming
- Check codec compatibility (H.264, MJPEG)
- Try different protocol (RTSP vs HTTP)

### General Troubleshooting Steps

1. **Check Logs**: Enable debug logging to see detailed connection attempts
2. **Network Connectivity**: Use `ping` and `telnet` to test basic connectivity
3. **Camera Reset**: Power cycle cameras if experiencing persistent issues
4. **Configuration Validation**: Verify JSON configuration syntax
5. **Port Conflicts**: Ensure no other services are using camera ports

## Security Considerations

### Network Camera Security

- **Authentication**: Always use strong passwords for camera access
- **Network Segmentation**: Place cameras on separate VLANs when possible
- **Encryption**: Use HTTPS for HTTP streams when available
- **Access Control**: Limit camera access to necessary services only

### Bluetooth Security

- **Pairing**: Use secure pairing methods when available
- **Range Limitation**: Bluetooth cameras have limited range, reducing unauthorized access
- **Encryption**: Verify Bluetooth connection uses encryption if supported

### General Security Best Practices

- **Credential Management**: Store camera credentials securely (environment variables, secrets management)
- **Network Monitoring**: Monitor for unauthorized access attempts
- **Firmware Updates**: Keep camera firmware updated for security patches
- **Physical Security**: Protect cameras from physical tampering

## API Endpoints

The Edge Processor integrates with the API Gateway for camera management:

- `GET /cameras`: List all managed cameras
- `POST /cameras/bluetooth`: Add Bluetooth camera
- `POST /cameras/cctv`: Add CCTV camera
- `DELETE /cameras/{id}`: Remove camera
- `GET /cameras/{id}/status`: Get camera status

## Monitoring and Health Checks

The service provides comprehensive monitoring:

- **Connection Status**: Real-time connection state for all cameras
- **Frame Rate Monitoring**: Track video stream health
- **Reconnection Attempts**: Monitor automatic recovery
- **Event Statistics**: Track detection events sent to Kafka

## Dependencies

- `opencv-python`: Video processing and camera connectivity
- `pybluez`: Bluetooth camera support
- `mtcnn`: Face detection
- `kafka-python`: Event streaming
- `structlog`: Structured logging
- `numpy`: Image processing
- `Pillow`: Image encoding

## Running the Service

```bash
# Using Docker Compose
docker-compose up edge-processor

# Direct execution
python main.py
```

## Architecture

The service follows a modular architecture:

- `CameraManager`: Central camera management and monitoring
- `BaseCamera`: Abstract camera interface
- `BluetoothCamera`: Bluetooth camera implementation
- `CCTVCamera`: Network camera implementation
- `EdgeProcessor`: Main processing logic and event generation