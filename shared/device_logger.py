"""
Enhanced Device Logger for IRIS devices.

Provides structured logging with MQTT transmission for crash analysis and debugging.
Includes system stats, memory usage, and error context for troubleshooting.

Usage:
    from shared.device_logger import DeviceLogger
    
    logger = DeviceLogger(runtime, device_id="garage-controller")
    logger.info("app", "Application started", {"version": "1.0.0"})
    logger.error("sensors", "BMP388 read failed", {"error": str(e), "retries": 3})
    logger.critical("bootstrap", "System crash imminent", {"free_memory": gc.mem_free()})
"""

try:
    import time
    import gc
    import machine
    import micropython
    HAS_MICROPYTHON = True
except (ImportError, AttributeError):
    # Running on desktop Python for testing
    import time
    import sys as machine
    HAS_MICROPYTHON = False
    class MockMicropython:
        def mem_info(self, verbose=False): return None
        def stack_use(self): return 0
    micropython = MockMicropython()

try:
    import ujson as json
except ImportError:
    import json


class DeviceLogger:
    """Enhanced device logger with MQTT transmission and system context.
    
    Provides structured logging with automatic system stats, memory info,
    and crash analysis data. Logs are sent via MQTT for centralized debugging.
    
    Attributes:
        runtime: Bootstrap runtime API for MQTT publishing
        device_id (str): Device identifier
        sequence (int): Auto-incrementing sequence number for log ordering
        log_topic (str): MQTT topic for device logs
        buffer (list): Buffered logs waiting to be sent
        buffer_size (int): Maximum logs to buffer before forcing transmission
        min_level (str): Minimum log level to transmit
    """
    
    LEVELS = {
        'DEBUG': 10,
        'INFO': 20,
        'WARNING': 30,
        'ERROR': 40,
        'CRITICAL': 50
    }
    
    def __init__(self, runtime, device_id: str, buffer_size: int = 10, min_level: str = 'INFO'):
        """Initialize device logger.
        
        Args:
            runtime: Bootstrap runtime API
            device_id (str): Device identifier
            buffer_size (int): Max logs to buffer before transmission
            min_level (str): Minimum level to transmit (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.runtime = runtime
        self.device_id = device_id
        self.sequence = 0
        self.log_topic = f"home/system/{device_id}/log"
        self.buffer = []
        self.buffer_size = buffer_size
        self.min_level = min_level
        self._min_level_num = self.LEVELS.get(min_level.upper(), 20)
        self._last_flush = self._ticks_ms()
        
        # Log system info at startup
        try:
            self.info("logger", "Device logger initialized", self._get_system_info())
        except Exception:
            pass
    
    def _ticks_ms(self) -> int:
        """Get current time in milliseconds."""
        try:
            if HAS_MICROPYTHON:
                return time.ticks_ms()
            else:
                return int(time.time() * 1000)
        except Exception:
            return 0
    
    def _get_system_info(self) -> dict:
        """Collect system information for log context."""
        info = {
            "uptime_ms": self._ticks_ms(),
            "sequence": self.sequence,
        }
        
        try:
            if HAS_MICROPYTHON:
                # MicroPython system stats
                info["free_memory"] = gc.mem_free()
                info["allocated_memory"] = gc.mem_alloc()
                info["stack_use"] = micropython.stack_use()
                
                # Try to get CPU temperature (if available)
                try:
                    sensor = machine.ADC(machine.ADC.CORE_TEMP)
                    reading = sensor.read_u16() * 3.3 / (65535)
                    temp_c = 27 - (reading - 0.706) / 0.001721
                    info["cpu_temp_c"] = round(temp_c, 1)
                except Exception:
                    pass
                
                # WiFi stats if available
                try:
                    import network
                    wlan = network.WLAN(network.STA_IF)
                    if wlan.isconnected():
                        info["wifi_rssi"] = wlan.status('rssi') if hasattr(wlan, 'status') else None
                        info["wifi_ip"] = wlan.ifconfig()[0]
                except Exception:
                    pass
            else:
                # Desktop Python (for testing)
                import psutil
                info["free_memory"] = psutil.virtual_memory().available
                info["cpu_percent"] = psutil.cpu_percent()
        except Exception:
            pass
        
        return info
    
    def _should_log(self, level: str) -> bool:
        """Check if log level meets minimum threshold."""
        level_num = self.LEVELS.get(level.upper(), 20)
        return level_num >= self._min_level_num
    
    def _format_log(self, level: str, component: str, message: str, details: dict = None) -> dict:
        """Format log entry for MQTT transmission."""
        self.sequence += 1
        
        log_entry = {
            "level": level.upper(),
            "component": component,
            "message": message,
            "timestamp": self._ticks_ms(),
            "sequence": self.sequence,
        }
        
        # Merge system info with provided details
        full_details = self._get_system_info()
        if details:
            full_details.update(details)
        
        # Only include details if there are any
        if full_details:
            log_entry["details"] = full_details
        
        return log_entry
    
    def _send_log(self, log_entry: dict):
        """Send single log entry via MQTT."""
        try:
            payload = json.dumps(log_entry)
            self.runtime.publish(self.log_topic, payload)
        except Exception as e:
            # If we can't send logs, at least print to console
            try:
                print(f"[LOG_ERROR] Failed to send log: {e}")
                print(f"[LOG_DATA] {log_entry}")
            except Exception:
                pass
    
    def _flush_buffer(self, force: bool = False):
        """Flush buffered logs to MQTT."""
        now = self._ticks_ms()
        
        # Flush if buffer is full, forced, or it's been too long since last flush
        should_flush = (
            force or 
            len(self.buffer) >= self.buffer_size or
            (self.buffer and (now - self._last_flush) > 60000)  # 1 minute
        )
        
        if should_flush and self.buffer:
            for log_entry in self.buffer:
                self._send_log(log_entry)
            self.buffer.clear()
            self._last_flush = now
    
    def _log(self, level: str, component: str, message: str, details: dict = None, immediate: bool = False):
        """Internal logging method."""
        if not self._should_log(level):
            return
        
        log_entry = self._format_log(level, component, message, details)
        
        # For critical errors or immediate logs, send right away
        if immediate or level.upper() in ('ERROR', 'CRITICAL'):
            self._send_log(log_entry)
            self._flush_buffer()  # Also flush any buffered logs
        else:
            # Buffer non-critical logs
            self.buffer.append(log_entry)
            self._flush_buffer()  # Check if buffer should be flushed
    
    def debug(self, component: str, message: str, details: dict = None):
        """Log debug message."""
        self._log('DEBUG', component, message, details)
    
    def info(self, component: str, message: str, details: dict = None):
        """Log info message."""
        self._log('INFO', component, message, details)
    
    def warning(self, component: str, message: str, details: dict = None):
        """Log warning message."""
        self._log('WARNING', component, message, details)
    
    def error(self, component: str, message: str, details: dict = None, immediate: bool = True):
        """Log error message (sent immediately by default)."""
        self._log('ERROR', component, message, details, immediate)
    
    def critical(self, component: str, message: str, details: dict = None, immediate: bool = True):
        """Log critical message (sent immediately by default)."""
        self._log('CRITICAL', component, message, details, immediate)
    
    def log_exception(self, component: str, exception: Exception, context: str = "", immediate: bool = True):
        """Log exception with full context."""
        details = {
            "exception_type": type(exception).__name__,
            "exception_str": str(exception),
            "context": context,
        }
        
        # Try to get traceback info if available
        try:
            import sys
            import io
            if hasattr(sys, 'exc_info'):
                import traceback
                tb_str = io.StringIO()
                traceback.print_exc(file=tb_str)
                details["traceback"] = tb_str.getvalue()
        except Exception:
            pass
        
        self._log('ERROR', component, f"Exception in {context}: {exception}", details, immediate)
    
    def flush(self):
        """Force flush all buffered logs."""
        self._flush_buffer(force=True)
    
    def set_level(self, level: str):
        """Change minimum logging level."""
        self.min_level = level.upper()
        self._min_level_num = self.LEVELS.get(self.min_level, 20)
    
    def log_system_stats(self, component: str = "system"):
        """Log current system statistics."""
        stats = self._get_system_info()
        self.info(component, "System status", stats)


# Convenience functions for quick logging
def create_logger(runtime, device_id: str) -> DeviceLogger:
    """Create and return a device logger instance."""
    return DeviceLogger(runtime, device_id)


# Global logger instance (set by bootstrap)
_global_logger = None


def set_global_logger(logger: DeviceLogger):
    """Set the global logger instance."""
    global _global_logger
    _global_logger = logger


def get_logger() -> DeviceLogger:
    """Get the global logger instance."""
    return _global_logger


# Convenience functions using global logger
def debug(component: str, message: str, details: dict = None):
    """Log debug message using global logger."""
    if _global_logger:
        _global_logger.debug(component, message, details)


def info(component: str, message: str, details: dict = None):
    """Log info message using global logger."""
    if _global_logger:
        _global_logger.info(component, message, details)


def warning(component: str, message: str, details: dict = None):
    """Log warning message using global logger."""
    if _global_logger:
        _global_logger.warning(component, message, details)


def error(component: str, message: str, details: dict = None, immediate: bool = True):
    """Log error message using global logger."""
    if _global_logger:
        _global_logger.error(component, message, details, immediate)


def critical(component: str, message: str, details: dict = None, immediate: bool = True):
    """Log critical message using global logger."""
    if _global_logger:
        _global_logger.critical(component, message, details, immediate)


def log_exception(component: str, exception: Exception, context: str = ""):
    """Log exception using global logger."""
    if _global_logger:
        _global_logger.log_exception(component, exception, context)


def flush_logs():
    """Flush all buffered logs using global logger."""
    if _global_logger:
        _global_logger.flush()
