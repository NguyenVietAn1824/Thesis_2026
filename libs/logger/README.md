(# Logger Library)

Value
-----

- **Purpose**: Configure and provide structured logging utilities for the application using `structlog` and Python's `logging`.
- **Why it matters**: Centralized logging configuration ensures consistent formats (JSON or pretty console), structured events for observability, and safe handling of uncaught exceptions.
- **When to use**: Call `setup_logging()` at application startup and use `get_logger()` to obtain a structured logger in modules.
