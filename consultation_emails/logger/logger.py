import logging
import os

import boto3
import watchtower
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

LOGGER_LEVELS = {"LOCAL": logging.DEBUG, "DEV": logging.INFO, "PREPROD": logging.WARNING, "PROD": logging.ERROR}
logger_level = os.environ["ENVIRONMENT"]
logger.setLevel(LOGGER_LEVELS.get(logger_level))

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

if logger_level != "LOCAL":
    try:
        logs_client = boto3.client("logs", region_name=os.environ["REGION"])
        cw_handler = watchtower.CloudWatchLogHandler(
            log_group=f"/ecs/extract-app-{logger_level.lower()}",
            stream_name="extract-app",
            boto3_client=logs_client,
        )
        cw_handler.setFormatter(formatter)
        logger.addHandler(cw_handler)
    except Exception as e:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.warning("Failed to initialize CloudWatch logging: %s", str(e))
else:
    # Console logging for local
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
