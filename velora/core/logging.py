"""
Logging configuration for Velora
"""

import logging
import sys
from typing import Optional, Dict, Any
import structlog
from structlog.stdlib import LoggerFactory
from pythonjsonlogger import jsonlogger
from velora.core.config import get_settings


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Set up structured logging for Velora
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    settings = get_settings()
    log_level = log_level or settings.log_level
    
    # Configure Python's logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Configure JSON formatter for production
    if settings.is_production:
        logHandler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        logHandler.setFormatter(formatter)
        logging.root.handlers = [logHandler]
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            ),
            structlog.processors.dict_tracebacks,
            structlog.dev.ConsoleRenderer() if settings.is_development else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger instance for the class"""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__module__)
        return self._logger
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self.logger.debug(message, **kwargs)
    
    def log_info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self.logger.info(message, **kwargs)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self.logger.warning(message, **kwargs)
    
    def log_error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log error message"""
        if error:
            kwargs["error"] = str(error)
            kwargs["error_type"] = type(error).__name__
        self.logger.error(message, **kwargs)
    
    def log_critical(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log critical message"""
        if error:
            kwargs["error"] = str(error)
            kwargs["error_type"] = type(error).__name__
        self.logger.critical(message, **kwargs)