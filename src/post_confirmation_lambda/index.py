import json
import os
import logging
from datetime import datetime
from boto3 import resource, client
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    dynamodb_resource = resource('dynamodb')
    dynamodb_client = client('dynamodb') # Needed for TransactWriteItems
    USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME')
    if not USERS_TABLE_NAME:
        raise ValueError("Environment variable USERS_TABLE_NAME is not set.")
    users_table = dynamodb_resource.Table(USERS_TABLE_NAME)
except Exception as e:
    logger.critical(f"Failed to initialize AWS clients or get table name: {str(e)}")
    raise e # Raise to prevent further execution

def lambda_handler(event, context):
    """
    Post confirmation Lambda trigger for Cognito.
    - Retrieves user data including 'custom:user_id' set by Pre Sign-up Lambda.
    - Writes user PROFILE, IDENTITY, and SETTINGS items to DynamoDB.
    - Assumes Single Table Design.
    - Attempts to create PROFILE/SETTINGS only if they don't exist for the user_id.
    - Always attempts to create the specific IDENTITY confirmed by this event, if not already present.
    """
    logger.info(f"Received event: {json.dumps(event)}")

    if not users_table:
        logger.error("DynamoDB table not initialized. Exiting.")
        # Returning the event allows Cognito flow to complete, but DB state is incomplete.
        return event

    # Only process sign-up confirmation events
    trigger_source = event.get('triggerSource')
    if trigger_source != 'PostConfirmation_ConfirmSignUp':
        logger.info(f"Trigger source is {trigger_source}, not PostConfirmation_ConfirmSignUp. Skipping DB operations.")
        return event

    try:
        # ---- Get user attributes ----
        user_attributes = event['request'].get('userAttributes', {})
        cognito_sub = user_attributes.get('sub')
        # *** CRITICAL: Get user_id assigned by Pre Sign-up Lambda ***
        user_id = user_attributes.get('custom:user_id')
        user_pool_id = event['userPoolId']
        username = event['userName'] # Cognito username (could be UUID, email, or custom)

        # Check if essential IDs are present
        if not cognito_sub:
            logger.error(f"Cognito 'sub' attribute missing for username {username}. Cannot proceed.")
            raise ValueError(f"Missing Cognito 'sub' for {username}") # Raise to stop further processing
        if not user_id:
            # This is a critical failure if the Pre Sign-up Lambda is supposed to always set it.
            logger.error(f"CRITICAL: 'custom:user_id' attribute missing for username {username} / sub {cognito_sub}. Pre Sign-up trigger may have failed or is misconfigured. Cannot write to DynamoDB.")
            raise ValueError(f"custom:user_id missing for {username}") # Raise to stop further processing

        logger.info(f"Processing confirmation for user_id: {user_id}, cognito_sub: {cognito_sub}, email: {email}")

        # ---- Determine identity provider ----
        provider = "COGNITO" # Default if not federated
        federated_details = {}
        if 'identities' in user_attributes:
            try:
                identity_info_list = json.loads(user_attributes.get('identities', '[]'))
                if identity_info_list and len(identity_info_list) > 0:
                    # Assume the first identity is the relevant one for this confirmation
                    identity_info = identity_info_list[0]
                    provider = identity_info.get('providerName', 'COGNITO').upper()
                    federated_details = {
                         'federatedUserId': identity_info.get('userId', ''),
                         'federatedIssuer': identity_info.get('issuer', ''),
                         'federatedDateCreated': identity_info.get('dateCreated', '')
                    }
                    logger.info(f"Federated login detected from provider: {provider}")
            except Exception as e:
                logger.warning(f"Failed to parse identities attribute: {user_attributes.get('identities')}. Error: {str(e)}")
                # Proceeding with provider as COGNITO

        # ---- Prepare DynamoDB Items ----
        timestamp = datetime.utcnow().isoformat() + "Z" # Use ISO 8601 format with Z for UTC

        identity_item = {
            'PK': f"USER#{user_id}",
            'SK': f"IDENTITY#{provider}",
            'providerSub': cognito_sub,
            'provider': provider,
        }
        # Add federated details if they exist
        identity_item.update(federated_details)

        # ---- Attempt to write to DynamoDB ----
        try:
            # Step 1: Always try to put the Identity Item for this confirmation
            # Use ConditionExpression to avoid overwriting if it somehow exists
            logger.info(f"Attempting to put IDENTITY item for provider {provider}, user_id {user_id}")
            users_table.put_item(
                Item=identity_item,
                ConditionExpression='attribute_not_exists(PK) AND attribute_not_exists(SK)'
            )
            logger.info(f"Successfully put IDENTITY item for provider {provider}")

            # Step 2: Try to create the main user PROFILE and SETTINGS items
            # Use a transaction for atomicity, with conditions to only create if they don't exist.
            logger.info(f"Attempting transaction to create PROFILE and SETTINGS for user_id {user_id} if they don't exist.")

            # Define Minimal PROFILE Item
            profile_item = {
                'PK': f"USER#{user_id}",
                'SK': "PROFILE",
                'userId': user_id,
                'status': 'ACTIVE',
                'createdAt': timestamp,
                'updatedAt': timestamp,
                'entityType': 'USER'
            }

            # Define Minimal SETTINGS Item
            settings_item = {
                'PK': f"USER#{user_id}",
                'SK': "SETTINGS",
                'entityType': 'SETTINGS',
                'createdAt': timestamp,
                'updatedAt': timestamp,
                'preferences': { 'theme': 'light', 'language': 'en' },
                'notifications': { 'marketing': { 'email': False } }
            }

            # Execute the transaction to add PROFILE and SETTINGS
            transaction_items = [
                {
                    'Put': {
                        'TableName': USERS_TABLE_NAME,
                        'Item': profile_item,
                        'ConditionExpression': 'attribute_not_exists(PK)' # Only add if PROFILE doesn't exist
                    }
                },
                {
                    'Put': {
                        'TableName': USERS_TABLE_NAME,
                        'Item': settings_item,
                        'ConditionExpression': 'attribute_not_exists(PK)' # Only add if SETTINGS doesn't exist
                    }
                }
            ]

            try:
                dynamodb_client.transact_write_items(TransactItems=transaction_items)
                logger.info(f"Successfully created new PROFILE and SETTINGS for user_id {user_id}")
            except ClientError as e:
                # Specifically check for conditional check failure
                if e.response['Error']['Code'] == 'TransactionCanceledException' and \
                   any('ConditionalCheckFailed' in reason.get('Code', '') for reason in e.response.get('CancellationReasons', [])):
                   logger.info(f"PROFILE and/or SETTINGS already exist for user_id {user_id}. Transaction conditional check failed, which is expected on subsequent identity confirmations.")
                else:
                    # Log other transaction errors
                    logger.error(f"DynamoDB transaction failed for PROFILE/SETTINGS creation: {str(e)}")

        except ClientError as e:
            # Handle error from the initial IDENTITY put_item call
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.info(f"IDENTITY item for provider {provider} already exists for user_id {user_id}. Skipping.")
            else:
                logger.error(f"Error writing IDENTITY item to DynamoDB: {str(e)}")
                return event


        logger.info(f"Successfully processed confirmation for user_id: {user_id}")
        return event

    except Exception as e:
        logger.error(f"FATAL: Unhandled error in post confirmation Lambda for username {event.get('userName','UNKNOWN')}: {str(e)}", exc_info=True)
        # Logged error, allow confirmation to succeed in Cognito.
        # Consider re-raising if DB consistency is paramount: raise e
        return event