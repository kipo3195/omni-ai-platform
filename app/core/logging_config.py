import logging


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        # Uvicorn may configure logging before importing the application.
        # Reconfigure the root logger so application INFO logs are not discarded.
        force=True,
    )
