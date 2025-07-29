import logging


def setup_logging(
    name: str | None = None, level: int = logging.DEBUG
) -> logging.Logger:
    """Set up basic logging and return a named logger."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(name)
