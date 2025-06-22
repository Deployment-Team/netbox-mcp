#!/usr/bin/env python3
"""
Enterprise Structured Logging Configuration for NetBox MCP

Provides JSON-structured logging for enterprise deployment with:
- Structured JSON output for log aggregation systems
- Correlation IDs for request tracing
- Performance metrics integration
- Security-focused log filtering
- Multi-environment configuration support

Features:
- ELK Stack / Splunk / Datadog compatible JSON format
- Request correlation tracking
- Performance timing integration
- Secrets masking for security
- Configurable log levels per component
"""

import json
import logging
import logging.config
import time
import uuid
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
from pathlib import Path
import inspect
import threading

from .secrets import get_secrets_manager


class CorrelationContextManager:
    """Thread-local correlation ID management for request tracing."""
    
    def __init__(self):
        self._local = threading.local()
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for current thread."""
        self._local.correlation_id = correlation_id
    
    def get_correlation_id(self) -> Optional[str]:
        """Get correlation ID for current thread."""
        return getattr(self._local, 'correlation_id', None)
    
    def generate_correlation_id(self) -> str:
        """Generate new correlation ID and set it for current thread."""
        correlation_id = str(uuid.uuid4())[:8]
        self.set_correlation_id(correlation_id)
        return correlation_id
    
    def clear_correlation_id(self):
        """Clear correlation ID for current thread."""
        if hasattr(self._local, 'correlation_id'):
            delattr(self._local, 'correlation_id')


# Global correlation context manager
correlation_context = CorrelationContextManager()


class StructuredFormatter(logging.Formatter):
    """
    JSON structured log formatter for enterprise log aggregation.
    
    Produces logs in structured JSON format compatible with:
    - ELK Stack (Elasticsearch, Logstash, Kibana)
    - Splunk Enterprise
    - Datadog Logs
    - AWS CloudWatch Logs
    - Azure Monitor Logs
    """
    
    def __init__(self, service_name: str = "netbox-mcp", service_version: str = "0.6.0"):
        super().__init__()
        self.service_name = service_name
        self.service_version = service_version
        self.secrets_manager = get_secrets_manager()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        
        # Base log structure
        log_entry = {
            # Standard fields
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            
            # Service identification
            "service": {
                "name": self.service_name,
                "version": self.service_version
            },
            
            # Source location
            "source": {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
                "module": record.module
            },
            
            # Process/thread information
            "process": {
                "pid": record.process,
                "thread_name": record.threadName,
                "thread_id": record.thread
            }
        }
        
        # Add correlation ID if available
        correlation_id = correlation_context.get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add custom fields from log record
        custom_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                # Mask secrets in custom fields
                if isinstance(value, str) and self._looks_like_secret(key, value):
                    custom_fields[key] = self._mask_secret_value(value)
                else:
                    custom_fields[key] = value
        
        if custom_fields:
            log_entry["custom"] = custom_fields
        
        # Add performance timing if available
        if hasattr(record, 'duration_ms'):
            log_entry["performance"] = {
                "duration_ms": record.duration_ms
            }
        
        # Add NetBox operation context if available
        if hasattr(record, 'netbox_operation'):
            log_entry["netbox"] = {
                "operation": record.netbox_operation,
                "endpoint": getattr(record, 'netbox_endpoint', None),
                "object_type": getattr(record, 'netbox_object_type', None),
                "object_id": getattr(record, 'netbox_object_id', None),
                "dry_run": getattr(record, 'netbox_dry_run', None)
            }
        
        # Add HTTP request context if available
        if hasattr(record, 'http_method'):
            log_entry["http"] = {
                "method": record.http_method,
                "path": getattr(record, 'http_path', None),
                "status_code": getattr(record, 'http_status_code', None),
                "user_agent": getattr(record, 'http_user_agent', None),
                "remote_addr": getattr(record, 'http_remote_addr', None)
            }
        
        return json.dumps(log_entry, default=str)
    
    def _looks_like_secret(self, key: str, value: str) -> bool:
        """Heuristic to detect if a field might contain secrets."""
        secret_indicators = [
            'token', 'password', 'secret', 'key', 'credential', 
            'auth', 'api_key', 'api_token', 'bearer'
        ]
        key_lower = key.lower()
        return any(indicator in key_lower for indicator in secret_indicators)
    
    def _mask_secret_value(self, value: str) -> str:
        """Mask secret values for safe logging."""
        if len(value) <= 4:
            return "***"
        return "***" + value[-4:]


class PerformanceLoggerMixin:
    """Mixin to add performance timing to log records."""
    
    def log_with_timing(self, level: int, msg: str, start_time: float, **kwargs):
        """Log message with performance timing."""
        duration_ms = (time.time() - start_time) * 1000
        extra = kwargs.get('extra', {})
        extra['duration_ms'] = round(duration_ms, 3)
        kwargs['extra'] = extra
        self.log(level, msg, **kwargs)


class NetBoxOperationLogger(logging.Logger, PerformanceLoggerMixin):
    """Specialized logger for NetBox operations."""
    
    def netbox_operation(self, level: int, msg: str, operation: str, 
                        endpoint: str = None, object_type: str = None, 
                        object_id: Union[int, str] = None, dry_run: bool = None, 
                        start_time: float = None, **kwargs):
        """Log NetBox operation with structured context."""
        extra = kwargs.get('extra', {})
        extra.update({
            'netbox_operation': operation,
            'netbox_endpoint': endpoint,
            'netbox_object_type': object_type,
            'netbox_object_id': object_id,
            'netbox_dry_run': dry_run
        })
        
        if start_time is not None:
            duration_ms = (time.time() - start_time) * 1000
            extra['duration_ms'] = round(duration_ms, 3)
        
        kwargs['extra'] = extra
        self.log(level, msg, **kwargs)
    
    def netbox_read(self, msg: str, endpoint: str, start_time: float = None, **kwargs):
        """Log NetBox read operation."""
        self.netbox_operation(logging.INFO, msg, "read", endpoint=endpoint, 
                            start_time=start_time, **kwargs)
    
    def netbox_write(self, msg: str, operation: str, object_type: str, 
                    object_id: Union[int, str] = None, dry_run: bool = None, 
                    start_time: float = None, **kwargs):
        """Log NetBox write operation."""
        self.netbox_operation(logging.WARNING if not dry_run else logging.INFO, 
                            msg, operation, object_type=object_type, 
                            object_id=object_id, dry_run=dry_run, 
                            start_time=start_time, **kwargs)
    
    def netbox_error(self, msg: str, operation: str, error: Exception, 
                    endpoint: str = None, start_time: float = None, **kwargs):
        """Log NetBox operation error."""
        extra = kwargs.get('extra', {})
        extra.update({
            'netbox_operation': operation,
            'netbox_endpoint': endpoint,
            'error_type': type(error).__name__,
            'error_message': str(error)
        })
        
        if start_time is not None:
            duration_ms = (time.time() - start_time) * 1000
            extra['duration_ms'] = round(duration_ms, 3)
        
        kwargs['extra'] = extra
        self.error(msg, exc_info=True, **kwargs)


# Register custom logger class
logging.setLoggerClass(NetBoxOperationLogger)\n\n\ndef setup_structured_logging(\n    log_level: str = \"INFO\",\n    log_format: str = \"json\",\n    log_file: Optional[str] = None,\n    service_name: str = \"netbox-mcp\",\n    service_version: str = \"0.6.0\",\n    enable_console: bool = True,\n    enable_file: bool = False\n) -> Dict[str, Any]:\n    \"\"\"\n    Setup enterprise structured logging configuration.\n    \n    Args:\n        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)\n        log_format: Format type (\"json\" for structured, \"text\" for human-readable)\n        log_file: Optional log file path\n        service_name: Service name for log identification\n        service_version: Service version for log identification\n        enable_console: Enable console logging\n        enable_file: Enable file logging\n        \n    Returns:\n        Dictionary with logging configuration\n    \"\"\"\n    \n    # Determine formatters\n    formatters = {}\n    \n    if log_format == \"json\":\n        formatters[\"structured\"] = {\n            \"()\": StructuredFormatter,\n            \"service_name\": service_name,\n            \"service_version\": service_version\n        }\n        default_formatter = \"structured\"\n    else:\n        formatters[\"standard\"] = {\n            \"format\": \"%(asctime)s [%(levelname)8s] %(name)s: %(message)s\",\n            \"datefmt\": \"%Y-%m-%d %H:%M:%S\"\n        }\n        default_formatter = \"standard\"\n    \n    # Setup handlers\n    handlers = {}\n    root_handlers = []\n    \n    if enable_console:\n        handlers[\"console\"] = {\n            \"class\": \"logging.StreamHandler\",\n            \"formatter\": default_formatter,\n            \"level\": log_level,\n            \"stream\": \"ext://sys.stdout\"\n        }\n        root_handlers.append(\"console\")\n    \n    if enable_file and log_file:\n        # Ensure log directory exists\n        log_path = Path(log_file)\n        log_path.parent.mkdir(parents=True, exist_ok=True)\n        \n        handlers[\"file\"] = {\n            \"class\": \"logging.handlers.RotatingFileHandler\",\n            \"filename\": log_file,\n            \"formatter\": default_formatter,\n            \"level\": log_level,\n            \"maxBytes\": 10 * 1024 * 1024,  # 10MB\n            \"backupCount\": 5,\n            \"encoding\": \"utf-8\"\n        }\n        root_handlers.append(\"file\")\n    \n    # Configure component-specific log levels\n    loggers = {\n        \"netbox_mcp\": {\n            \"level\": log_level,\n            \"handlers\": root_handlers,\n            \"propagate\": False\n        },\n        \"netbox_mcp.client\": {\n            \"level\": log_level\n        },\n        \"netbox_mcp.server\": {\n            \"level\": log_level\n        },\n        \"netbox_mcp.tools\": {\n            \"level\": log_level\n        },\n        \"netbox_mcp.secrets\": {\n            \"level\": \"WARNING\"  # Reduce secrets manager verbosity\n        },\n        # External library log levels\n        \"urllib3\": {\n            \"level\": \"WARNING\"\n        },\n        \"requests\": {\n            \"level\": \"WARNING\"\n        },\n        \"pynetbox\": {\n            \"level\": \"INFO\"\n        }\n    }\n    \n    # Complete logging configuration\n    config = {\n        \"version\": 1,\n        \"disable_existing_loggers\": False,\n        \"formatters\": formatters,\n        \"handlers\": handlers,\n        \"loggers\": loggers,\n        \"root\": {\n            \"level\": log_level,\n            \"handlers\": root_handlers\n        }\n    }\n    \n    return config\n\n\ndef configure_logging(\n    log_level: str = \"INFO\",\n    log_format: str = \"json\",\n    log_file: Optional[str] = None,\n    service_name: str = \"netbox-mcp\",\n    service_version: str = \"0.6.0\"\n):\n    \"\"\"\n    Configure and apply structured logging settings.\n    \n    Args:\n        log_level: Logging level\n        log_format: Format type (\"json\" or \"text\")\n        log_file: Optional log file path\n        service_name: Service name\n        service_version: Service version\n    \"\"\"\n    \n    # Determine if we're in a container/production environment\n    is_production = Path(\"/app\").exists() or Path(\"/run/secrets\").exists()\n    \n    # Configure structured logging\n    config = setup_structured_logging(\n        log_level=log_level,\n        log_format=\"json\" if is_production else log_format,\n        log_file=log_file,\n        service_name=service_name,\n        service_version=service_version,\n        enable_console=True,\n        enable_file=bool(log_file)\n    )\n    \n    # Apply configuration\n    logging.config.dictConfig(config)\n    \n    # Create correlation ID for this session\n    correlation_context.generate_correlation_id()\n    \n    # Log successful configuration\n    logger = logging.getLogger(\"netbox_mcp.logging\")\n    logger.info(\"Structured logging configured\", extra={\n        \"log_level\": log_level,\n        \"log_format\": log_format,\n        \"log_file\": log_file,\n        \"service_name\": service_name,\n        \"service_version\": service_version,\n        \"is_production\": is_production\n    })\n\n\ndef get_logger(name: str) -> NetBoxOperationLogger:\n    \"\"\"\n    Get a logger instance with NetBox operation support.\n    \n    Args:\n        name: Logger name\n        \n    Returns:\n        NetBoxOperationLogger instance\n    \"\"\"\n    return logging.getLogger(name)\n\n\n# Context managers for request correlation\nclass correlation_id:\n    \"\"\"Context manager for setting correlation ID for a block of code.\"\"\"\n    \n    def __init__(self, correlation_id: str = None):\n        self.correlation_id = correlation_id or str(uuid.uuid4())[:8]\n        self.previous_id = None\n    \n    def __enter__(self):\n        self.previous_id = correlation_context.get_correlation_id()\n        correlation_context.set_correlation_id(self.correlation_id)\n        return self.correlation_id\n    \n    def __exit__(self, exc_type, exc_val, exc_tb):\n        if self.previous_id:\n            correlation_context.set_correlation_id(self.previous_id)\n        else:\n            correlation_context.clear_correlation_id()\n\n\nclass operation_timing:\n    \"\"\"Context manager for timing operations and logging results.\"\"\"\n    \n    def __init__(self, logger: logging.Logger, operation_name: str, level: int = logging.INFO):\n        self.logger = logger\n        self.operation_name = operation_name\n        self.level = level\n        self.start_time = None\n    \n    def __enter__(self):\n        self.start_time = time.time()\n        return self\n    \n    def __exit__(self, exc_type, exc_val, exc_tb):\n        duration_ms = (time.time() - self.start_time) * 1000\n        \n        if exc_type is None:\n            # Success\n            self.logger.log(self.level, f\"{self.operation_name} completed\", \n                          extra={'duration_ms': round(duration_ms, 3)})\n        else:\n            # Error\n            self.logger.error(f\"{self.operation_name} failed\", \n                            extra={'duration_ms': round(duration_ms, 3)}, \n                            exc_info=True)\n\n\n# Export main functions\n__all__ = [\n    'configure_logging',\n    'get_logger',\n    'StructuredFormatter',\n    'NetBoxOperationLogger',\n    'correlation_id',\n    'operation_timing',\n    'correlation_context'\n]