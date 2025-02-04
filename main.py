import os
import sys
import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from openai import OpenAI
from flask import Flask, jsonify, request
from flask_cors import CORS
from tenacity import retry, stop_after_attempt, wait_exponential

def validate_environment():
    """
    Validate critical environment configurations
    """
    critical_env_vars = [
        'SECRET_KEY',
        'OPENAI_API_KEY',
        'FLASK_ENV'
    ]
    
    missing_vars = [var for var in critical_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing critical environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

def create_required_directories():
    """
    Create necessary directories for the application
    """
    required_dirs = [
        'logs',
        'data/form_fields',
        'templates/forms',
        'uploads',
        'temp'
    ]
    
    for directory in required_dirs:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
            sys.exit(1)

def configure_logging(app):
    """
    Set up comprehensive logging configuration
    """
    # Ensure logs directory exists
    logs_dir = 'logs'
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create file handler with rotation
    log_file = os.path.join(logs_dir, 'legal_case_manager.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    # Set logging format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Set logging levels
    log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
    file_handler.setLevel(log_level)
    console_handler.setLevel(log_level)
    
    # Configure app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)
    
    # Log startup information
    app.logger.info("Logging configured successfully")

def configure_openai_client(app):
    """
    Configure OpenAI client with error handling
    """
    try:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        app.config['openai_client'] = OpenAI(api_key=openai_api_key)
        app.logger.info("OpenAI client configured successfully")
    except Exception as e:
        app.logger.error(f"Failed to configure OpenAI client: {e}")
        sys.exit(1)

def configure_app(app):
    """
    Configure application settings and environment variables
    """
    # Load environment variables
    load_dotenv()
    
    # Validate critical environment variables
    validate_environment()
    
    # Create required directories
    create_required_directories()
    
    # Set secret key
    app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
    
    # Enable CORS
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Configure logging
    configure_logging(app)
    
    # Configure OpenAI client
    configure_openai_client(app)
    
    # Additional configuration
    app.config.update(
        ENV=os.getenv('FLASK_ENV', 'production'),
        DEBUG=os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
        TESTING=os.getenv('FLASK_TESTING', 'False').lower() == 'true',
        MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16 MB max file upload
    )
    
    return app

def create_app():
    """
    Application factory
    """
    from app import create_app as app_factory
    
    # Create Flask app
    app = app_factory()
    
    # Configure the app
    return configure_app(app)

# Advanced Error Handlers
def register_error_handlers(app):
    """
    Register global error handlers
    """
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "error": "Bad Request",
            "message": str(error),
            "status": 400
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "error": "Unauthorized",
            "message": str(error),
            "status": 401
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "error": "Forbidden",
            "message": str(error),
            "status": 403
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Not Found",
            "message": str(error),
            "status": 404
        }), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"Internal Server Error: {str(error)}")
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status": 500
        }), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.error(f"Unexpected Error: {str(error)}")
        return jsonify({
            "error": "Unexpected Error",
            "message": "An unexpected error occurred",
            "status": 500
        }), 500

def main():
    """
    Main entry point for the application
    """
    try:
        # Create and configure app
        app = create_app()
        
        # Register error handlers
        register_error_handlers(app)
        
        # Determine host and port
        host = os.getenv('APP_HOST', '0.0.0.0')
        port = int(os.getenv('APP_PORT', 5000))
        
        # Log startup information
        app.logger.info(f"Starting Legal Case Management Application")
        app.logger.info(f"Host: {host}")
        app.logger.info(f"Port: {port}")
        app.logger.info(f"Environment: {app.config['ENV']}")
        app.logger.info(f"Debug Mode: {app.config['DEBUG']}")
        
        # Run the application
        app.run(
            host=host,
            port=port,
            debug=app.config['DEBUG']
        )
    
    except Exception as e:
        # Log any fatal startup errors
        if 'app' in locals():
            app.logger.error(f"Fatal error during application startup: {e}")
        else:
            print(f"Fatal error during application startup: {e}")
        
        sys.exit(1)

if __name__ == '__main__':
    main()