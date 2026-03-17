import logging


def configure_logging(log_level: str) -> None:
    normalized_level = log_level.upper()
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(normalized_level)
        return

    logging.basicConfig(
        level=normalized_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

