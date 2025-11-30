"""
Structured JSON logging for TabSage

Based on Day 4a: Agent Observability
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False
    # Fallback to standard logging
    import logging as jsonlogger


class StructuredLogger:
    """Structured JSON logger for TabSage agents"""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        self.logger.handlers = []
        
        # JSON formatter
        json_handler = logging.StreamHandler(sys.stdout)
        if HAS_JSON_LOGGER:
            formatter = jsonlogger.JsonFormatter(
                '%(timestamp)s %(level)s %(name)s %(message)s',
                timestamp=True
            )
        else:
            # Fallback to standard formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        json_handler.setFormatter(formatter)
        self.logger.addHandler(json_handler)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with structured data"""
        exc_info = kwargs.pop('exc_info', False)
        extra = {
            "log_timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.logger.log(level, message, extra=extra, exc_info=exc_info)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)
    
    def agent_start(self, agent_name: str, session_id: str, payload: Dict[str, Any]):
        """Log agent start"""
        self.info(
            f"Agent {agent_name} started",
            event_type="agent_start",
            agent_name=agent_name,
            session_id=session_id,
            payload_keys=list(payload.keys())
        )
    
    def agent_complete(self, agent_name: str, session_id: str, duration_ms: float):
        """Log agent completion"""
        self.info(
            f"Agent {agent_name} completed",
            event_type="agent_complete",
            agent_name=agent_name,
            session_id=session_id,
            duration_ms=duration_ms
        )
    
    def agent_error(self, agent_name: str, session_id: str, error: str):
        """Log agent error"""
        self.error(
            f"Agent {agent_name} failed",
            event_type="agent_error",
            agent_name=agent_name,
            session_id=session_id,
            error=error
        )
    
    def llm_request(self, agent_name: str, model: str, prompt_length: int):
        """Log LLM request"""
        self.debug(
            f"LLM request from {agent_name}",
            event_type="llm_request",
            agent_name=agent_name,
            model=model,
            prompt_length=prompt_length
        )
    
    def llm_response(self, agent_name: str, model: str, response_length: int, tokens: Optional[int] = None):
        """Log LLM response"""
        self.debug(
            f"LLM response to {agent_name}",
            event_type="llm_response",
            agent_name=agent_name,
            model=model,
            response_length=response_length,
            tokens=tokens
        )
    
    def tool_call(self, agent_name: str, tool_name: str, args: Dict[str, Any]):
        """Log tool call"""
        self.debug(
            f"Tool {tool_name} called by {agent_name}",
            event_type="tool_call",
            agent_name=agent_name,
            tool_name=tool_name,
            tool_args=list(args.keys())
        )
    
    def tool_result(self, agent_name: str, tool_name: str, success: bool, duration_ms: float):
        """Log tool result"""
        self.debug(
            f"Tool {tool_name} completed",
            event_type="tool_result",
            agent_name=agent_name,
            tool_name=tool_name,
            success=success,
            duration_ms=duration_ms
        )


# Global logger instances
_loggers: Dict[str, StructuredLogger] = {}


def setup_logging(
    level: int = logging.INFO,
    enable_json: bool = True,
    log_file: Optional[str] = None
) -> None:
    """Setup structured logging for TabSage
    
    Args:
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        enable_json: Enable JSON formatted logs
        log_file: Optional file to write logs to
    """
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    root_logger.handlers = []
    
    if enable_json and HAS_JSON_LOGGER:
        # JSON formatter for structured logs
        json_handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            timestamp=True
        )
        json_handler.setFormatter(formatter)
        root_logger.addHandler(json_handler)
    else:
        # Standard formatter
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        if enable_json:
            file_formatter = jsonlogger.JsonFormatter(
                '%(timestamp)s %(level)s %(name)s %(message)s',
                timestamp=True
            )
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    logging.info("Logging configured", extra={
        "event_type": "logging_setup",
        "level": logging.getLevelName(level),
        "json_enabled": enable_json
    })


def get_logger(name: str, level: int = logging.INFO) -> StructuredLogger:
    """Get or create a structured logger
    
    Args:
        name: Logger name (usually module name)
        level: Logging level
        
    Returns:
        StructuredLogger instance
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, level)
    return _loggers[name]

