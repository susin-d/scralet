# Config Directory

This directory contains configuration files for the Project Scarlet system, including camera connectivity settings, service configurations, and infrastructure setup.

## Camera Configuration

Project Scarlet supports multiple camera types with comprehensive configuration options for secure and reliable connectivity.

### Environment Variables for Camera Configuration

#### Bluetooth Camera Configuration

Configure Bluetooth cameras using the following environment variables:

```bash
# JSON array of Bluetooth camera configurations
BLUETOOTH_CAMERAS='[
  {
    "id": "bluetooth_front_door",
    "address": "AA:BB:CC:DD:EE:FF",
    "port": 1
  },
  {
    "id": "bluetooth_backyard",
    "address": "11:22:33:44:55:66",
    "port": 1
  }
]'

# Duration for Bluetooth device discovery (seconds)
BLUETOOTH_DISCOVERY_DURATION=8
```

#### CCTV Camera Configuration

Configure network CCTV cameras using RTSP or HTTP protocols:

```bash
# JSON array of CCTV camera configurations
CCTV_CAMERAS='[
  {
    "id": "cctv_entrance",
    "ip_address": "192.168.1.100",
    "port": 554,
    "protocol": "rtsp",
    "username": "admin",
    "password": "secure_password_123",
    "timeout": 10
  },
  {
    "id": "cctv_parking",
    "ip_address": "192.168.1.101",
    "port": 80,
    "protocol": "http",
    "username": "viewer",
    "password": "viewer_pass",
    "timeout": 15
  }
]'

# IP range for automatic CCTV camera discovery
CCTV_DISCOVERY_IP_RANGE=192.168.1.0/24

# Ports to scan during CCTV discovery (comma-separated)
CCTV_DISCOVERY_PORTS=554,80,8080
```

### Camera Configuration Parameters

#### Bluetooth Camera Parameters

- `id` (required): Unique identifier for the camera
- `address` (required): Bluetooth MAC address (format: AA:BB:CC:DD:EE:FF)
- `port` (optional): RFCOMM port number (default: 1)

#### CCTV Camera Parameters

- `id` (required): Unique identifier for the camera
- `ip_address` (required): IP address of the camera
- `port` (optional): Network port (default: 554 for RTSP, 80 for HTTP)
- `protocol` (optional): Streaming protocol - "rtsp" or "http" (default: "rtsp")
- `username` (optional): Authentication username
- `password` (optional): Authentication password
- `timeout` (optional): Connection timeout in seconds (default: 10)

### Camera Discovery Configuration

#### Bluetooth Discovery

- `BLUETOOTH_DISCOVERY_DURATION`: Time in seconds to scan for Bluetooth devices (default: 8)

#### Network Discovery

- `CCTV_DISCOVERY_IP_RANGE`: CIDR notation for IP range scanning (default: "192.168.1.0/24")
- `CCTV_DISCOVERY_PORTS`: Comma-separated list of ports to test (default: "554,80,8080")

### General Camera Settings

```bash
# Interval for camera health monitoring (seconds)
CAMERA_MONITOR_INTERVAL=10

# Kafka configuration for event streaming
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=camera-sighting-events
```

## Configuration Files

### docker-compose.yml

Main orchestration file containing service definitions, network configuration, and volume mounts.

### .env Files

Environment variable files for different deployment environments:

- `.env.local`: Local development configuration
- `.env.production`: Production environment settings

### Logstash Configuration

- `logstash.conf/`: Centralized logging configuration for aggregating service logs

## Security Considerations

### Camera Credentials

- Store camera passwords securely using environment variables
- Use strong, unique passwords for each camera
- Rotate credentials regularly
- Never commit credentials to version control

### Network Security

- Place cameras on secure network segments
- Use firewalls to restrict camera access
- Enable encryption for network streams when available
- Monitor for unauthorized access attempts

### Bluetooth Security

- Ensure Bluetooth cameras use secure pairing
- Limit Bluetooth range to prevent unauthorized connections
- Monitor for Bluetooth-based attacks

## Configuration Examples

### Complete .env File Example

```bash
# Camera Configuration
BLUETOOTH_CAMERAS='[{"id": "bt_cam_1", "address": "AA:BB:CC:DD:EE:FF"}]'
CCTV_CAMERAS='[{"id": "cctv_cam_1", "ip_address": "192.168.1.100", "username": "admin", "password": "secure_pass"}]'

# Discovery Settings
BLUETOOTH_DISCOVERY_DURATION=10
CCTV_DISCOVERY_IP_RANGE=192.168.1.0/24
CCTV_DISCOVERY_PORTS=554,80,8080

# Monitoring
CAMERA_MONITOR_INTERVAL=15

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC=camera-events

# Service Configuration
LOG_LEVEL=INFO
STORE_ZONE=main_store
```

### Docker Compose Environment Override

```yaml
services:
  edge-processor:
    env_file:
      - .env.local
    environment:
      - BLUETOOTH_CAMERAS=${BLUETOOTH_CAMERAS}
      - CCTV_CAMERAS=${CCTV_CAMERAS}
```

## Troubleshooting Configuration Issues

### Common Configuration Problems

1. **JSON Syntax Errors**: Validate JSON format using online tools
2. **Invalid IP Addresses**: Ensure IP addresses are in correct format and reachable
3. **Port Conflicts**: Check that camera ports are not used by other services
4. **Authentication Failures**: Verify camera credentials and permissions
5. **Bluetooth Connection Issues**: Ensure Bluetooth adapter is enabled and cameras are discoverable

### Validation Commands

```bash
# Test JSON syntax
python -c "import json; print(json.loads('${BLUETOOTH_CAMERAS}'))"

# Test network connectivity
ping 192.168.1.100

# Test camera ports
telnet 192.168.1.100 554
```

## Configuration Management

- Use version control for configuration templates (exclude secrets)
- Document configuration changes and their impact
- Test configuration changes in staging environments first
- Maintain backup configurations for disaster recovery