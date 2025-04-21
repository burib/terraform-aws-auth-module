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
    # Consider if retrying initialization makes sense or if failing fast is best.
    # Failing fast (raising) is usually safer for dependencies.
    raise e # Raise to prevent further execution

def lambda_handler(event, context):
    """
    Post confirmation Lambda trigger for Cognito. (Minimal, Non-PII Version)
    - Retrieves user data including 'custom:user_id' set by Pre Sign-up Lambda.
    - Writes minimal user PROFILE, IDENTITY, and SETTINGS items to DynamoDB.
    - Creates GSI for looking up user_id by cognito_sub via IDENTITY item.
    - Assumes Single Table Design.
    - Attempts to create PROFILE/SETTINGS only if they don't exist for the user_id.
    - Always attempts to create the specific IDENTITY confirmed by this event, if not already present.
    - Fails Lambda execution if essential IDs (sub, custom:user_id) are missing.
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Table initialization checked globally, but double-check can be added if needed.

    # Only process sign-up confirmation events
    trigger_source = event.get('triggerSource')
    if trigger_source != 'PostConfirmation_ConfirmSignUp':
        logger.info(f"Trigger source is {trigger_source}, not PostConfirmation_ConfirmSignUp. Skipping DB operations.")
        return event

    try:
        # ---- Get user attributes ----
        user_attributes = event['request'].get('userAttributes', {})
        cognito_sub = user_attributes.get('sub')
        user_id = user_attributes.get('custom:user_id') # Assigned by Pre Sign-up Lambda
        user_pool_id = event['userPoolId']
        username = event['userName'] # Cognito username

        # ---- Check if essential IDs are present ----
        if not cognito_sub:
            # Fail fast if Cognito identity cannot be linked
            logger.error(f"FATAL: Cognito 'sub' attribute missing for username {username}.")
            raise ValueError(f"Missing Cognito 'sub' for {username}")
        if not user_id:
            # Fail fast if internal user ID link is missing (Pre Sign-up issue)
            logger.error(f"FATAL: 'custom:user_id' attribute missing for username {username} / sub {cognito_sub}.")
            raise ValueError(f"custom:user_id missing for {username}")

        # Fixed log message - removed undefined 'email'
        logger.info(f"Processing confirmation for user_id: {user_id}, cognito_sub: {cognito_sub}")

        # ---- Determine identity provider ----
        provider = "COGNITO" # Default if not federated
        federated_details = {}
        if 'identities' in user_attributes:
            try:
                # Ensure robust parsing
                identities_str = user_attributes.get('identities', '[]')
                if identities_str: # Check if it's not None or empty string
                     identity_info_list = json.loads(identities_str)
                     if identity_info_list and len(identity_info_list) > 0:
                         # Assume the first identity is the relevant one for this confirmation
                         identity_info = identity_info_list[0]
                         provider = identity_info.get('providerName', 'COGNITO').upper()
                         federated_details = {
                              # Ensure values are fetched safely with .get()
                              'federatedUserId': identity_info.get('userId', ''),
                              'federatedIssuer': identity_info.get('issuer', ''),
                              'federatedDateCreated': identity_info.get('dateCreated', '')
                         }
                         logger.info(f"Federated login detected from provider: {provider}")
                else:
                    logger.warning("Received empty 'identities' attribute string.")
            except (json.JSONDecodeError, TypeError, IndexError) as e:
                logger.warning(f"Failed to parse 'identities' attribute: {user_attributes.get('identities')}. Error: {str(e)}")
                # Proceeding with provider as COGNITO

        # ---- Prepare DynamoDB Items ----
        timestamp = datetime.utcnow().isoformat() + "Z" # Use ISO 8601 format with Z for UTC

        # Enhanced identity_item (recommended)
        identity_item = {
            'PK': f"USER#{user_id}",
            'SK': f"IDENTITY#{provider}",
            'entityType': 'IDENTITY',           # Added
            'providerSub': cognito_sub,
            'provider': provider,
            'username': username,               # Optional: Added for debug context
            'createdAt': timestamp,             # Added
            # GSI for finding user by Cognito Sub (requires GSI named 'GSI2' with PK=GSI2PK, SK=GSI2SK)
            'GSI2PK': f"IDENT#{cognito_sub}",    # Added
            'GSI2SK': f"USER#{user_id}",        # Added
        }
        # Add federated details if they exist
        identity_item.update(federated_details) # federated_details only contains relevant keys

        # ---- Attempt to write to DynamoDB ----
        try:
            # Step 1: Always try to put the Identity Item for this confirmation
            logger.info(f"Attempting to put IDENTITY item for provider {provider}, user_id {user_id}")
            users_table.put_item(
                Item=identity_item,
                # Condition to ensure we don't overwrite *this specific* provider link if it somehow exists
                # Allows adding a COGNITO link even if a GOOGLE link exists, etc.
                ConditionExpression='attribute_not_exists(SK)' # Check only Sort Key (IDENTITY#{provider})
            )
            logger.info(f"Successfully put IDENTITY item for provider {provider}")

        except ClientError as e:
            # Handle error from the initial IDENTITY put_item call
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.info(f"IDENTITY item for provider {provider} already exists for user_id {user_id}. Skipping IDENTITY put.")
                # Okay to proceed, identity link already established.
            else:
                logger.error(f"DynamoDB ClientError writing IDENTITY item: {str(e)}")
                # Decide: Allow Cognito confirmation (return event) or enforce consistency (raise e)?
                # Raising ensures consistency but might block user on transient issue.
                # return event # Allows confirmation, risks inconsistency if this link fails
                raise e # Enforces consistency (recommended for critical link)


        # --- Transaction for PROFILE and SETTINGS ---
        # Only proceed to transaction if IDENTITY write was successful or condition check failed (meaning link exists)

        # Step 2: Try to create the main user PROFILE and SETTINGS items (transactionally)
        logger.info(f"Attempting transaction to create PROFILE and SETTINGS for user_id {user_id} if they don't exist.")

        # Define Minimal PROFILE Item
        profile_item = {
            'PK': f"USER#{user_id}",
            'SK': "PROFILE",
            'userId': user_id,              # Minimal: just the ID for reference
            'status': 'ACTIVE',             # Minimal: application status
            'createdAt': timestamp,         # Minimal: record creation time
            'updatedAt': timestamp,         # Minimal: same initially
            'entityType': 'USER'            # Minimal: type identifier
        }

        # Define Minimal SETTINGS Item
        settings_item = {
            'PK': f"USER#{user_id}",
            'SK': "SETTINGS",
            'entityType': 'SETTINGS',       # Minimal: type identifier
            'createdAt': timestamp,         # Minimal: record creation time
            'updatedAt': timestamp,         # Minimal: same initially
            # Minimal: essential non-PII preferences with generic defaults
            'preferences': { 'theme': 'light', 'language': 'en' },
            # Minimal: default opt-out for generic categories
            'notifications': { 'marketing': { 'email': False } }
        }

        # Execute the transaction to add PROFILE and SETTINGS
        transaction_items = [
            {
                'Put': {
                    'TableName': USERS_TABLE_NAME,
                    'Item': profile_item,
                    'ConditionExpression': 'attribute_not_exists(PK)' # Only add PROFILE if USER#{id} PK doesn't exist
                }
            },
            {
                'Put': {
                    'TableName': USERS_TABLE_NAME,
                    'Item': settings_item,
                     # ConditionExpression is on the Item in the list, refers to the Item being written
                    'ConditionExpression': 'attribute_not_exists(PK)' # Only add SETTINGS if USER#{id} PK doesn't exist
                }
            }
        ]

        try:
            dynamodb_client.transact_write_items(TransactItems=transaction_items)
            logger.info(f"Successfully created new PROFILE and SETTINGS via transaction for user_id {user_id}")
        except ClientError as e:
            # Specifically check for conditional check failure for the transaction
            if e.response['Error']['Code'] == 'TransactionCanceledException':
                 # Check cancellation reasons - it's possible only one item's condition failed
                 cancellation_reasons = e.response.get('CancellationReasons', [])
                 conditional_check_failed = any('ConditionalCheckFailed' in reason.get('Code', '') for reason in cancellation_reasons)
                 if conditional_check_failed:
                      logger.info(f"Transaction canceled because PROFILE and/or SETTINGS already exist for user_id {user_id}. Expected on subsequent identity confirmations.")
                      # If other reasons caused cancellation, log them more verbosely
                      non_conditional_reasons = [r for r in cancellation_reasons if 'ConditionalCheckFailed' not in r.get('Code', '')]
                      if non_conditional_reasons:
                           logger.warning(f"Transaction canceled for user_id {user_id} due to reasons other than/in addition to conditional checks: {non_conditional_reasons}")
                 else:
                     # Log unexpected cancellation reason
                     logger.error(f"DynamoDB transaction unexpectedly canceled for user_id {user_id}: {str(e)}")
                     raise e # Re-raise unexpected transaction cancellations
            else:
                # Log other transaction errors
                logger.error(f"DynamoDB ClientError during PROFILE/SETTINGS transaction: {str(e)}")
                # Decide: Allow confirmation (return event) or enforce consistency (raise e)?
                # return event # Risks inconsistency if profile/settings creation fails
                raise e # Enforces consistency (recommended for core user data)

        # If we reach here, all necessary DB operations succeeded or were gracefully handled (already exist)
        logger.info(f"Successfully processed confirmation for user_id: {user_id}")
        return event # Signal success back to Cognito

    except Exception as e:
        # Catch-all for unexpected errors during processing
        # The specific ValueErrors for missing IDs are caught above and re-raised implicitly
        logger.error(f"FATAL: Unhandled error in post confirmation Lambda for username {event.get('userName','UNKNOWN')}: {str(e)}", exc_info=True) # exc_info=True logs stack trace
        # Do not return event here, let the exception propagate to fail the Lambda/Confirmation
        raise e # Ensure Cognito knows the step failed critically