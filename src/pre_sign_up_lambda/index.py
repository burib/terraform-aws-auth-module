import json
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    # presignup trigger is meant for user validation only.

    logger.info(f"Returning event: {json.dumps(event)}")
    return event