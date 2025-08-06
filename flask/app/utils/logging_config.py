import logging

# Constants
LOG_LEVEL = logging.INFO


def initialize_logging(level: int = LOG_LEVEL):
    logging.basicConfig(level=level)
    return logging.getLogger(__name__)


# Initialize Logger
logger = initialize_logging()
