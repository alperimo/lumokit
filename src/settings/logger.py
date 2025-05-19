import logging
from datetime import datetime

import pytz

from settings.config import CONFIG

logger = logging.getLogger("LUMOKIT API")
log_level = CONFIG.LOG_LEVEL


class FastAPIFormatter(logging.Formatter):
    # Define color codes for different log levels
    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
    }
    RESET = "\033[0m"
    IST = pytz.timezone("Asia/Kolkata")

    def format(self, record):
        # Get the current time in IST
        ist_time = datetime.now(self.IST).strftime("%d-%m-%Y %H:%M:%S")

        # Format the log message
        log_message = f"[{ist_time}: {record.levelname}] Message: {record.getMessage()}"

        # Add color based on the log level
        color = self.COLORS.get(record.levelname, self.RESET)
        colored_message = f"{color}{log_message}{self.RESET}"

        return colored_message


formatter = FastAPIFormatter()

# General handler for all log levels
general_handler = logging.StreamHandler()
general_handler.setFormatter(formatter)

# Error handler to always show errors
error_handler = logging.StreamHandler()
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(general_handler)
logger.addHandler(error_handler)

# Set the logger level based on the configuration
match log_level:
    case "CRITICAL" | "critical":
        logger.setLevel(logging.CRITICAL)
    case "ERROR" | "error":
        logger.setLevel(logging.ERROR)
    case "WARNING" | "warning" | "WARN" | "warn":
        logger.setLevel(logging.WARNING)
    case "DEBUG" | "debug":
        logger.setLevel(logging.DEBUG)
    case "INFO" | "info" | _:
        logger.setLevel(logging.INFO)
