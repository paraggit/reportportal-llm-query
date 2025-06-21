import sys
from pathlib import Path

from loguru import logger

from src.utils.config import Config


def setup_logger(config: Config):
    """Configure loguru logger."""
    # Remove default handler
    logger.remove()

    # Create logs directory
    logs_dir = Path(config.paths.logs_dir)
    logs_dir.mkdir(exist_ok=True)

    # Console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    # File handler for all logs
    logger.add(
        logs_dir / "app.log",
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
    )

    # File handler for errors
    logger.add(
        logs_dir / "errors.log",
        rotation="1 week",
        retention="1 month",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
    )

    logger.info("Logger initialized")
