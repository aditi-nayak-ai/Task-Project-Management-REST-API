import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root.handlers = [handler]

    for noisy in ("sqlalchemy.engine", "alembic", "passlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


logger = logging.getLogger("app")
