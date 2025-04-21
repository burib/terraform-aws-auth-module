import json
import os
import logging
from uuidv7 import uuidv7

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Pre sign-up Lambda trigger for Cognito.
    Generates a new custom user_id (UUIDv7) for every sign-up attempt
    and adds it as a custom attribute 'custom:user_id'.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    user_id = None

    try:
        # Generate a new, unique user ID for this sign-up attempt
        user_id = str(uuidv7())
        logger.info(f"Generated new UUIDv7 userId: {user_id} for username {event.get('userName', 'UNKNOWN')}")

        # ---- Add the custom user_id to the event response ----
        # Set default response values (adjust if needed)
        event['response']['autoConfirmUser'] = False
        event['response']['autoVerifyEmail'] = False
        event['response']['autoVerifyPhone'] = False

        # IMPORTANT: Add/Update the custom attribute in the request context
        # Cognito uses this to create the user.
        if 'userAttributes' not in event['request']:
             event['request']['userAttributes'] = {} # Ensure dict exists

        event['request']['userAttributes']['custom:user_id'] = user_id
        logger.info(f"Successfully set custom:user_id = {user_id} for username {event.get('userName', 'UNKNOWN')}")

    except Exception as e:
        logger.error(f"Error in Pre Sign-up Lambda: {str(e)}")
        print(f"CRITICAL: Failed to set custom:user_id for {event.get('userName', 'UNKNOWN')}. Error: {str(e)}")
        raise e


    # Return the modified event to Cognito
    logger.info(f"Returning event: {json.dumps(event)}")
    return event