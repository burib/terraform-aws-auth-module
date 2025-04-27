import json
import os
import logging
import hashlib
from datetime import datetime
from boto3 import resource, client
from botocore.exceptions import ClientError
from uuidv7 import uuidv7

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    dynamodb_resource = resource('dynamodb')
    dynamodb_client = client('dynamodb')
    cognito_client = client('cognito-idp')
    USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME')
    if not USERS_TABLE_NAME:
        raise ValueError("Environment variable USERS_TABLE_NAME is not set.")
    users_table = dynamodb_resource.Table(USERS_TABLE_NAME)
except Exception as e:
    logger.critical(f"Failed to initialize AWS clients or get table name: {str(e)}")
    raise e

# Environment variables for tenant determination strategy
TENANT_STRATEGY = os.environ.get('TENANT_STRATEGY', 'domain') # 'domain', 'invitation', 'personal', 'strict'
ALLOW_PERSONAL_TENANTS = os.environ.get('ALLOW_PERSONAL_TENANTS', 'true').lower() == 'true'
DOMAIN_TENANT_MAP = json.loads(os.environ.get('DOMAIN_TENANT_MAP', '{}'))
ALLOWED_DOMAINS = json.loads(os.environ.get('ALLOWED_DOMAINS', '[]'))
REQUIRE_TENANT = os.environ.get('REQUIRE_TENANT', 'false').lower() == 'true'

def determine_tenant_id(event):
    """
    Determine tenant ID from the event context using a configurable strategy.
    
    Available strategies:
    1. Explicit attribute - Use if tenant_id is already in user attributes
    2. Invitation - Check for invitation code in client metadata
    3. Domain mapping - Map email domains to tenant IDs 
    4. Personal tenant - Create user-specific tenant
    
    Configuration is via environment variables:
    - TENANT_STRATEGY: Main strategy to use ('domain', 'invitation', 'personal', 'strict')
    - ALLOW_PERSONAL_TENANTS: Whether to create personal tenants as fallback (true/false)
    - DOMAIN_TENANT_MAP: JSON mapping of email domains to tenant IDs
    - ALLOWED_DOMAINS: JSON array of allowed email domains
    - REQUIRE_TENANT: Whether to raise error if no tenant can be determined (true/false)
    """
    user_attributes = event['request'].get('userAttributes', {})
    client_metadata = event.get('callerContext', {}).get('clientMetadata', {})
    email = user_attributes.get('email', '')
    username = event.get('userName', '')
    
    # STRATEGY 1: Use explicit tenant_id if already provided
    # This is useful for admin-created users or specific signup flows
    if 'custom:tenant_id' in user_attributes:
        tenant_id = user_attributes['custom:tenant_id']
        logger.info(f"Using explicit tenant_id from user attributes: {tenant_id}")
        return tenant_id
    
    # STRATEGY 2: Check for invitation flow
    # Invitations contain tenant context and are more secure
    invitation_code = client_metadata.get('invitation_code')
    invitation_tenant = client_metadata.get('invitation_tenant_id')
    
    if invitation_tenant:
        logger.info(f"Using tenant from invitation metadata: {invitation_tenant}")
        return invitation_tenant
    
    if invitation_code and TENANT_STRATEGY == 'invitation':
        # Note: In a real implementation, you would verify the invitation code
        # against a database of valid invitations
        logger.warning(f"Invitation code provided but verification not implemented: {invitation_code}")
        # For now, extract tenant from code if format is 'TENANT:CODE'
        if ':' in invitation_code:
            tenant_id = invitation_code.split(':')[0]
            logger.info(f"Extracted tenant from invitation code: {tenant_id}")
            return tenant_id
    
    # STRATEGY 3: App client mapping
    # Map different app clients to different tenants
    client_id = event.get('callerContext', {}).get('clientId')
    if client_id:
        # This would typically be a lookup from environment variables or database
        # Example: tenant_map = json.loads(os.environ.get('CLIENT_TENANT_MAP', '{}'))
        tenant_map = {
            # Map client IDs to tenant IDs - customize based on your needs
            # 'abc123clientid': 'tenant1',
            # 'def456clientid': 'tenant2'
        }
        if client_id in tenant_map:
            tenant_id = tenant_map[client_id]
            logger.info(f"Mapped client ID {client_id} to tenant: {tenant_id}")
            return tenant_id
    
    # STRATEGY 4: Domain-based tenant mapping
    # Extract tenant from email domain using configurable mapping
    if email and '@' in email and (TENANT_STRATEGY == 'domain' or TENANT_STRATEGY == 'strict'):
        domain = email.split('@')[1].lower()
        
        # Check if domain is in allowed list (if configured)
        if ALLOWED_DOMAINS and domain not in ALLOWED_DOMAINS:
            if REQUIRE_TENANT:
                raise ValueError(f"Email domain {domain} is not allowed for registration")
        
        # Check for domain in explicit mapping
        if domain in DOMAIN_TENANT_MAP:
            tenant_id = DOMAIN_TENANT_MAP[domain]
            logger.info(f"Mapped email domain {domain} to tenant: {tenant_id}")
            return tenant_id
            
        # Use domain as tenant ID if no mapping
        if not DOMAIN_TENANT_MAP and domain:
            # Extract subdomain or use full domain
            domain_parts = domain.split('.')
            potential_tenant = domain_parts[0]
            if potential_tenant and potential_tenant not in ['gmail', 'hotmail', 'yahoo', 'outlook', 'icloud']:
                logger.info(f"Using domain part as tenant ID: {potential_tenant}")
                return potential_tenant
    
    # STRATEGY 5: Personal tenant (unique per user)
    if ALLOW_PERSONAL_TENANTS or TENANT_STRATEGY == 'personal':
        # Create a deterministic but unique tenant ID based on email or username
        identifier = email if email else username
        hash_val = hashlib.md5(identifier.encode()).hexdigest()[:8]
        personal_tenant_id = f"personal-{hash_val}"
        logger.info(f"Created personal tenant ID: {personal_tenant_id}")
        return personal_tenant_id
    
    # No tenant could be determined
    if REQUIRE_TENANT:
        logger.error(f"Could not determine tenant ID and REQUIRE_TENANT is set")
        raise ValueError("Unable to determine tenant ID for user registration")
    
    # Last resort fallback - should not typically be reached with proper configuration
    logger.warning("Using emergency fallback tenant - THIS IS NOT RECOMMENDED FOR PRODUCTION")
    return "unassigned"  # This should be handled specially in your application

def lambda_handler(event, context):
    """
    Post confirmation Lambda trigger for Cognito with multi-tenant support.
    - Determines tenant context for the user using secure strategies
    - Adds tenant_id to user attributes in Cognito
    - Creates tenant-aware database records without duplicating sensitive user data
    - Supports users belonging to multiple tenants
    """
    logger.info(f"Received event: {json.dumps(event)}")
    user_id = None

    # Only process sign-up confirmation events
    trigger_source = event.get('triggerSource')
    if trigger_source != 'PostConfirmation_ConfirmSignUp':
        logger.info(f"Trigger source is {trigger_source}, not PostConfirmation_ConfirmSignUp. Skipping DB operations.")
        return event

    try:
        # Get user attributes
        user_attributes = event['request'].get('userAttributes', {})
        cognito_sub = user_attributes.get('sub')
        user_pool_id = event['userPoolId']
        username = event['userName']
        email = user_attributes.get('email', '')

        # Check essential IDs
        if not cognito_sub:
            logger.error(f"FATAL: Cognito 'sub' attribute missing for username {username}.")
            raise ValueError(f"Missing Cognito 'sub' for {username}")

        # Determine tenant context using secure strategies
        try:
            tenant_id = determine_tenant_id(event)
            if not tenant_id:
                logger.error("Empty tenant ID returned from determination function")
                raise ValueError("Tenant determination failed - empty tenant ID")
            
            logger.info(f"Determined tenant_id: {tenant_id} for user: {username}")
        except Exception as e:
            logger.error(f"Tenant determination failed: {str(e)}")
            raise
            
        # Generate new user_id
        user_id = str(uuidv7())
        logger.info(f"Generated new user_id: {user_id} for username: {username}")

        # Determine identity provider
        provider = "COGNITO"  # Default if not federated
        federated_details = {}
        if 'identities' in user_attributes:
            try:
                identities_str = user_attributes.get('identities', '[]')
                if identities_str:
                    identity_info_list = json.loads(identities_str)
                    if identity_info_list and len(identity_info_list) > 0:
                        identity_info = identity_info_list[0]
                        provider = identity_info.get('providerName', 'COGNITO').upper()
                        federated_details = {
                            'federatedUserId': identity_info.get('userId', ''),
                            'federatedIssuer': identity_info.get('issuer', ''),
                            'federatedDateCreated': identity_info.get('dateCreated', '')
                        }
                        logger.info(f"Federated login detected from provider: {provider}")
                else:
                    logger.warning("Received empty 'identities' attribute string.")
            except (json.JSONDecodeError, TypeError, IndexError) as e:
                logger.warning(f"Failed to parse 'identities' attribute: {user_attributes.get('identities')}. Error: {str(e)}")

        # Prepare DynamoDB Items
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Multi-tenant identity_item with tenant context 
        # but WITHOUT storing email (since it's in Cognito)
        identity_item = {
            'PK': f"TENANT#{tenant_id}#USER#{user_id}",  
            'SK': f"IDENTITY#{provider}",
            'entityType': 'IDENTITY',
            'providerSub': cognito_sub,
            'provider': provider,
            'username': username,
            'tenantId': tenant_id,  # Store tenant ID explicitly
            'createdAt': timestamp,
            # GSI for finding user by Cognito Sub
            'GSI2PK': f"IDENT#{cognito_sub}",
            'GSI2SK': f"TENANT#{tenant_id}#USER#{user_id}",  # Include tenant in value
            # Tenant-specific GSI for queries within tenant
            'GSI3PK': f"TENANT#{tenant_id}",
            'GSI3SK': f"USER#{user_id}"
        }
        
        # Add federated details if they exist
        identity_item.update(federated_details)

        # Attempt to write identity item to DynamoDB
        try:
            logger.info(f"Attempting to put IDENTITY item for provider {provider}, user_id {user_id} in tenant {tenant_id}")
            users_table.put_item(
                Item=identity_item,
                ConditionExpression='attribute_not_exists(SK)'
            )
            logger.info(f"Successfully put IDENTITY item for provider {provider}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.info(f"IDENTITY item for provider {provider} already exists for user_id {user_id} in tenant {tenant_id}. Skipping IDENTITY put.")
            else:
                logger.error(f"DynamoDB ClientError writing IDENTITY item: {str(e)}")
                raise e

        # Multi-tenant profile WITHOUT email (stored in Cognito)
        profile_item = {
            'PK': {'S': f"TENANT#{tenant_id}#USER#{user_id}"},
            'SK': {'S': "PROFILE"},
            'userId': {'S': user_id},
            'tenantId': {'S': tenant_id},
            'status': {'S': 'ACTIVE'},
            'createdAt': {'S': timestamp},
            'updatedAt': {'S': timestamp},
            'entityType': {'S': 'USER'},
            'GSI3PK': {'S': f"TENANT#{tenant_id}"},
            'GSI3SK': {'S': f"USER#{user_id}"}
            # No email stored here - that stays in Cognito
        }

        # User settings item
        settings_item = {
            'PK': {'S': f"TENANT#{tenant_id}#USER#{user_id}"},
            'SK': {'S': "SETTINGS"},
            'entityType': {'S': 'SETTINGS'},
            'tenantId': {'S': tenant_id},
            'createdAt': {'S': timestamp},
            'updatedAt': {'S': timestamp},
            'preferences': {'M': {
                'theme': {'S': 'light'},
                'language': {'S': 'en'}
              }
            },
            'notifications': {'M': {
                'marketing': {'M': {
                    'email': {'BOOL': False}
                  }
                }
              }
            },
            'GSI3PK': {'S': f"TENANT#{tenant_id}"},
            'GSI3SK': {'S': f"USER#{user_id}"}
        }

        # Tenant membership item for multi-tenant user support
        tenant_membership_item = {
            'PK': {'S': f"USER#{user_id}"},
            'SK': {'S': f"TENANT#{tenant_id}"},
            'status': {'S': 'ACTIVE'},
            'role': {'S': 'member'},
            'joinedAt': {'S': timestamp},
            'tenantId': {'S': tenant_id},
            'GSI4PK': {'S': f"USER#{user_id}"},
            'GSI4SK': {'S': f"TENANT#{tenant_id}"}
        }
        
        # Special handling for personal tenants - make user admin of their personal tenant
        if tenant_id.startswith('personal-'):
            tenant_membership_item['role'] = {'S': 'admin'}

        # Transaction for PROFILE, SETTINGS, and TENANT_MEMBERSHIP
        transaction_items = [
            {
                'Put': {
                    'TableName': USERS_TABLE_NAME,
                    'Item': profile_item,
                    'ConditionExpression': 'attribute_not_exists(PK)'
                }
            },
            {
                'Put': {
                    'TableName': USERS_TABLE_NAME,
                    'Item': settings_item,
                    'ConditionExpression': 'attribute_not_exists(PK)'
                }
            },
            {
                'Put': {
                    'TableName': USERS_TABLE_NAME,
                    'Item': tenant_membership_item,
                    'ConditionExpression': 'attribute_not_exists(PK)'
                }
            }
        ]

        try:
            dynamodb_client.transact_write_items(TransactItems=transaction_items)
            logger.info(f"Successfully created new PROFILE, SETTINGS, and TENANT_MEMBERSHIP via transaction for user_id {user_id} in tenant {tenant_id}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'TransactionCanceledException':
                cancellation_reasons = e.response.get('CancellationReasons', [])
                conditional_check_failed = any('ConditionalCheckFailed' in reason.get('Code', '') for reason in cancellation_reasons)
                if conditional_check_failed:
                    logger.info(f"Transaction canceled because one or more items already exist for user_id {user_id} in tenant {tenant_id}.")
                    non_conditional_reasons = [r for r in cancellation_reasons if 'ConditionalCheckFailed' not in r.get('Code', '')]
                    if non_conditional_reasons:
                        logger.warning(f"Transaction canceled for user_id {user_id} due to reasons other than/in addition to conditional checks: {non_conditional_reasons}")
                else:
                    logger.error(f"DynamoDB transaction unexpectedly canceled for user_id {user_id}: {str(e)}")
                    raise e
            else:
                logger.error(f"DynamoDB ClientError during transaction: {str(e)}")
                raise e

        # Update Cognito Custom Attributes
        try:
            logger.info(f"Attempting to set custom:user_id={user_id} and custom:tenant_id={tenant_id} in Cognito for username {username}")
            cognito_client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=username,
                UserAttributes=[
                    {
                        'Name': 'custom:user_id',
                        'Value': user_id
                    },
                    {
                        'Name': 'custom:tenant_id',
                        'Value': tenant_id
                    },
                ]
            )
            logger.info(f"Successfully set custom attributes in Cognito for username {username}")
        except ClientError as e:
            logger.error(f"Failed to set custom attributes in Cognito for username {username}: {str(e)}")
            raise e

        logger.info(f"Successfully processed confirmation for user_id: {user_id} in tenant: {tenant_id}")
        return event

    except Exception as e:
        logger.error(f"FATAL: Unhandled error in post confirmation Lambda for username {event.get('userName','UNKNOWN')}: {str(e)}", exc_info=True)
        raise e