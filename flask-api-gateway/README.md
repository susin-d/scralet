# Flask API Gateway

A Flask-based API Gateway service for the Project Scarlet retail analytics system. This service provides a centralized entry point for all client requests, handles authentication, routing, and real-time WebSocket connections.

## Features

- **Flask Application Factory**: Modular Flask app creation with proper configuration management
- **JWT Authentication**: Secure admin authentication with JSON Web Tokens
- **WebSocket Support**: Real-time communication using Flask-SocketIO
- **CORS Support**: Cross-origin resource sharing for frontend integration
- **Service Routing**: Proxy requests to backend microservices
- **Admin Dashboard**: User management and system monitoring
- **Structured Logging**: JSON-formatted logging with structlog

## Architecture

The Flask API Gateway follows a modular architecture:

```
flask-api-gateway/
├── flask_api_gateway/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # Flask app factory and routes
│   └── config.py            # Configuration management
├── run.py                   # Entry point script
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Configuration

The service supports environment-based configuration through the `Config` class in `config.py`. Key configuration options include:

- **Service URLs**: URLs for backend microservices
- **JWT Settings**: Secret key, algorithm, and token expiration
- **Flask Settings**: Host, port, debug mode, CORS origins
- **SocketIO Settings**: CORS allowed origins
- **Admin Credentials**: Default admin username and password

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_HOST` | `0.0.0.0` | Flask server host |
| `FLASK_PORT` | `8000` | Flask server port |
| `FLASK_DEBUG` | `False` | Enable debug mode |
| `JWT_SECRET_KEY` | `your-secret-key-here` | JWT signing key |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token expiration |
| `USER_SERVICE_URL` | `http://user-service:8001` | User service URL |
| `EDGE_PROCESSOR_URL` | `http://edge-processor:8000` | Edge processor URL |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed CORS origins |

## API Endpoints

### Authentication
- `POST /admin/login` - Admin user login
- `POST /admin/logout` - Admin user logout

### Admin Management
- `GET /admin/users` - List admin users
- `POST /admin/users` - Create admin user
- `DELETE /admin/users/{username}` - Delete admin user

### Dashboard
- `GET /admin/dashboard/stats` - Dashboard statistics
- `GET /admin/logs` - System logs

### Public API
- `POST /register` - Customer registration
- `GET /cameras` - Camera list
- `GET /logs` - Event logs
- `GET /alerts/count` - Alert count

### WebSocket
- `/ws/dashboard` - Real-time dashboard updates

## Installation

1. **Clone the repository** (if applicable) and navigate to the flask-api-gateway directory:
   ```bash
   cd flask-api-gateway
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Service

### Development Mode
```bash
python run.py
```

### Production Mode
Set environment variables and run:
```bash
export FLASK_ENV=production
export FLASK_DEBUG=False
python run.py
```

### Using Docker
```bash
docker build -t flask-api-gateway .
docker run -p 8000:8000 flask-api-gateway
```

## Dependencies

- **Flask**: Web framework
- **Flask-CORS**: Cross-origin resource sharing
- **Flask-JWT-Extended**: JWT authentication
- **Flask-SocketIO**: WebSocket support
- **requests**: HTTP client for service communication
- **structlog**: Structured logging

## Development

### Code Structure
- `main.py`: Contains the Flask app factory, route definitions, and SocketIO event handlers
- `config.py`: Configuration management with environment variable support
- `run.py`: Entry point script for starting the server

### Adding New Routes
1. Define route functions in `main.py` within the `register_routes` function
2. Use appropriate decorators for authentication (`@jwt_required()`) and HTTP methods
3. Add proper error handling and logging

### WebSocket Events
Add new SocketIO event handlers in the `register_socketio_events` function:
```python
@socketio.on('custom_event')
def handle_custom_event(data):
    # Handle custom event
    emit('response_event', response_data)
```

## Security Considerations

- **JWT Tokens**: Use strong secret keys and short expiration times
- **Password Storage**: Implement proper password hashing (currently using plain text for demo)
- **CORS**: Configure appropriate origins for production
- **Input Validation**: Validate all user inputs and API requests
- **HTTPS**: Use HTTPS in production environments

## Monitoring

The service includes structured logging and can be integrated with monitoring tools like Prometheus for metrics collection.

## License

This project is part of the Project Scarlet system. See the main project README for licensing information.