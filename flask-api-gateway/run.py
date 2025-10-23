#!/usr/bin/env python3
"""
Entry point to start the Flask API Gateway server.
"""

import os
import sys
from flask_api_gateway.main import create_app
from flask_api_gateway.config import config

def main():
    """Main entry point for the Flask API Gateway."""
    # Add the current directory to Python path for imports
    sys.path.insert(0, os.path.dirname(__file__))

    # Create Flask app
    app = create_app()

    # Run the server
    print(f"Starting Flask API Gateway on {config.flask_host}:{config.flask_port}")
    print(f"Environment: {config.flask_env}")
    print(f"Debug mode: {config.flask_debug}")

    app.run(
        host=config.flask_host,
        port=config.flask_port,
        debug=config.flask_debug
    )

if __name__ == "__main__":
    main()