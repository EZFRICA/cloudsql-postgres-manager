"""
Enhanced logging configuration with centralized settings.
"""

import logging
import sys
from app.config import settings, get_log_level


def initialize_logging(level: int = None):
    """
    Initialize logging with configuration from settings.
    
    Args:
        level: Optional log level override
        
    Returns:
        Logger instance
    """
    if level is None:
        level = get_log_level()
    
    # Configure logging format
    formatter = logging.Formatter(settings.log_format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    
    return logging.getLogger(__name__)


# Initialize Logger
logger = initialize_logging()
