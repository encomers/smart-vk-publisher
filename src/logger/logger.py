import logging.config
from typing import Any

LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "level": "DEBUG",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": "project.log",
            "mode": "a",
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["default", "file"],
            "level": "DEBUG",
            "propagate": True,
        }
    },
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
