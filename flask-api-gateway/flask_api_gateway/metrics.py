from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Prometheus metrics
REQUEST_COUNT = Counter('flask_api_gateway_requests_total', 'Total number of requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('flask_api_gateway_request_duration_seconds', 'Request duration in seconds', ['method', 'endpoint'])


def get_metrics():
    """Get Prometheus metrics in the latest format."""
    return generate_latest()


def increment_request_count(method: str, endpoint: str, status: str):
    """Increment the request count metric."""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()


def time_request(method: str, endpoint: str):
    """Return a context manager to time a request."""
    return REQUEST_LATENCY.labels(method=method, endpoint=endpoint).time()