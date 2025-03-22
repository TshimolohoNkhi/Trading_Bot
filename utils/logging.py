import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("trader.log"), logging.StreamHandler()]
)
logger = logging.getLogger()

def setup_logging():
    return logger