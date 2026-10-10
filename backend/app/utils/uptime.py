"""
SYNAPSE uptime tracker — shared module to avoid circular imports.
Imported by main.py (sets start time) and health.py (reads it).
"""
import time

_start_time: float = 0.0


def set_start_time() -> None:
    """Called once at application startup."""
    global _start_time
    _start_time = time.time()


def get_uptime() -> float:
    """Return seconds since application startup."""
    return time.time() - _start_time
