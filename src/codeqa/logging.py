import logging
import sys 

import structlog 

from codeqa.config import get_settings


def configure_logging() -> None:
    """Configure sturctlog: JSON in prodduction, pretty console in development."""

    settings = get_settings()

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.stackInfoRenderer(),
    ]


    if settings.environment == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors = shared_processors + [renderer],
        wrapper_class = structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class = dict,
        logger_factory = structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use = True,
    )



def get_logger(name: str = "codeqa") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
