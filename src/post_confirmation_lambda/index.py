import json
import os
import logging
from datetime import datetime
from uuid_v7 import uuid7
from boto3 import resource, client

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients - more targeted imports
cognito_client = client('cognito-idp')
dynamodb_resource = resource('dynamodb')
dynamodb_client = client('dynamodb')
users_table = dynamodb_resource.Table(os.environ.get('USERS_TABLE_NAME', ''))

def lambda_handler(event, context):
    """
    Post confirmation Lambda trigger for Cognito.
    Implements Single Table Design pattern for user identity management.
    Uses UUIDv7 for time-sortable user IDs.
    
    Example events:
    
    1. Regular email signup confirmation:
    {
        "version": "1",
        "region": "us-east-1",
        "userPoolId": "us-east-1_aBcDeFgHi",
        "userName": "johndoe",
        "callerContext": {
            "awsSdkVersion": "aws-sdk-js-2.6.4",
            "clientId": "1abc2defghij3klmnop4qrstu"
        },
        "triggerSource": "PostConfirmation_ConfirmSignUp",
        "request": {
            "userAttributes": {
                "sub": "11112222-3333-4444-5555-666677778888",
                "email_verified": "true",
                "cognito:user_status": "CONFIRMED",
                "cognito:email_alias": "johndoe@example.com",
                "email": "johndoe@example.com"
            }
        },
        "response": {}
    }
    
    2. Google federated login confirmation:
    {
        "version": "1",
        "region": "us-east-1",
        "userPoolId": "us-east-1_aBcDeFgHi",
        "userName": "google_123456789",
        "callerContext": {
            "awsSdkVersion": "aws-sdk-js-2.6.4",
            "clientId": "1abc2defghij3klmnop4qrstu"
        },
        "triggerSource": "PostConfirmation_ConfirmSignUp",
        "request": {
            "userAttributes": {
                "sub": "99998888-7777-6666-5555-444433332222",
                "email_verified": "true",
                "cognito:user_status": "EXTERNAL_PROVIDER",
                "identities": "[{\"userId\":\"123456789\",\"providerName\":\"Google\",\"providerType\":\"Google\",\"issuer\":null,\"primary\":true,\"dateCreated\":1612345678}]",
                "email": "johndoe@gmail.com"
            }
        },
        "response": {}
    }
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Only process sign-up confirmation events
        if event.get('triggerSource') != 'PostConfirmation_ConfirmSignUp':
            logger.info(f"Not a confirmation event. Trigger source: {event.get('triggerSource')}")
            return event
            
        # Get user attributes
        user_attributes = event['request']['userAttributes']
        cognito_sub = user_attributes['sub']
        email = user_attributes.get('email', '').lower()  # Normalize email to lowercase
        user_pool_id = event['userPoolId']
        username = event['userName']
        
        # Determine if this is a federated identity
        provider = "COGNITO"
        if 'identities' in user_attributes:
            try:
                identity_info = json.loads(user_attributes['identities'])
                if identity_info and len(identity_info) > 0:
                    provider = identity_info[0].get('providerName', 'COGNITO').upper()
                    logger.info(f"Federated login detected from provider: {provider}")
            except Exception as e:
                logger.warning(f"Failed to parse identities attribute: {user_attributes.get('identities')}. Error: {str(e)}")
        
        # ---------------------------------------------------------------------
        # DynamoDB QUERY 1: Check if email exists (for identity linking)
        # - Uses GSI1 (Global Secondary Index) to find users by email
        # - GSI1PK = "EMAIL#{email}" is the partition key
        # - If found, we'll link this new login to existing user
        # - If not found, we'll create a new user
        # ---------------------------------------------------------------------
        try:
            logger.info(f"Checking if user with email {email} already exists")
            email_response = users_table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :email",
                ExpressionAttributeValues={
                    ":email": f"EMAIL#{email}"
                }
            )
            
            existing_user = False
            user_id = None
            
            if email_response.get('Items') and len(email_response['Items']) > 0:
                # FLOW: Existing user adding a new login method
                existing_user = True
                user_id = email_response['Items'][0]['GSI1SK'].replace("USER#", "")
                logger.info(f"Found existing user with email {email}, userId: {user_id}")
                
                # ---------------------------------------------------------------------
                # DynamoDB QUERY 2: Check if this provider is already linked
                # - Direct GetItem operation using PK and SK
                # - PK = "USER#{user_id}" is the partition key
                # - SK = "IDENTITY#{provider}" is the sort key
                # - Determines if this identity provider is already connected
                # ---------------------------------------------------------------------
                existing_identity_response = users_table.get_item(
                    Key={
                        'PK': f"USER#{user_id}",
                        'SK': f"IDENTITY#{provider}"
                    }
                )
                
                if 'Item' in existing_identity_response:
                    logger.info(f"Provider {provider} is already linked to user {user_id}")
                else:
                    logger.info(f"Linking new provider {provider} to existing user {user_id}")
            else:
                # FLOW: Brand new user signup
                # Generate sortable UUIDv7 for chronological ordering capability
                user_id = str(uuid7())
                logger.info(f"Generated new UUIDv7 userId: {user_id} for email: {email}")
                
            # ---------------------------------------------------------------------
            # Cognito Update: Set custom:user_id attribute
            # - This connects the Cognito identity with our custom ID system
            # - Essential for solving the "don't use Cognito sub as user ID" problem
            # ---------------------------------------------------------------------
            logger.info(f"Updating Cognito user {username} with custom user_id: {user_id}")
            cognito_client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=username,
                UserAttributes=[
                    {
                        'Name': 'custom:user_id',
                        'Value': user_id
                    }
                ]
            )
            
            # Get current timestamp
            timestamp = datetime.utcnow().isoformat()
            
            # ---------------------------------------------------------------------
            # DynamoDB Transaction: Atomic operation to maintain consistency
            # - Creates all necessary items in a single atomic operation
            # - Ensures identity system is always in a consistent state
            # - Handles both new user creation and identity linking patterns
            # ---------------------------------------------------------------------
            transaction_items = []
            
            if not existing_user:
                # ITEM 1: User profile item (main user record)
                # - PK: USER#{id}, SK: PROFILE creates unique composite key
                # - GSI1PK: EMAIL#{email}, GSI1SK: USER#{id} enables email lookup
                logger.info(f"Creating new user profile in DynamoDB for {user_id}")
                transaction_items.append({
                    'Put': {
                        'TableName': users_table.name,
                        'Item': {
                            'PK': f"USER#{user_id}",
                            'SK': "PROFILE",
                            'email': email,
                            'username': username,
                            'userPoolId': user_pool_id,
                            'createdAt': timestamp,
                            'updatedAt': timestamp,
                            'status': 'ACTIVE',
                            'entityType': 'USER',
                            'GSI1PK': f"EMAIL#{email}",
                            'GSI1SK': f"USER#{user_id}",
                            'firstName': user_attributes.get('given_name', ''),
                            'lastName': user_attributes.get('family_name', ''),
                            'locale': user_attributes.get('locale', 'en-US'),
                            'signupMethod': provider.lower()
                        },
                        'ConditionExpression': 'attribute_not_exists(PK)'
                    }
                })
            
            # ITEM 2: Identity item (links Cognito identity to our user)
            # - PK: USER#{id}, SK: IDENTITY#{provider} groups all identities under user
            # - GSI2PK: IDENT#{cognito_sub}, GSI2SK: USER#{id} enables cognito sub lookup
            # - This design allows one user to have multiple identity providers
            logger.info(f"Adding {provider} identity for user {user_id}")
            transaction_items.append({
                'Put': {
                    'TableName': users_table.name,
                    'Item': {
                        'PK': f"USER#{user_id}",
                        'SK': f"IDENTITY#{provider}",
                        'providerSub': cognito_sub,
                        'provider': provider,
                        'username': username,
                        'createdAt': timestamp,
                        'entityType': 'IDENTITY',
                        'GSI2PK': f"IDENT#{cognito_sub}",
                        'GSI2SK': f"USER#{user_id}",
                        'federatedUserId': json.loads(user_attributes.get('identities', '[]'))[0].get('userId', '') if 'identities' in user_attributes else '',
                        'federatedIssuer': json.loads(user_attributes.get('identities', '[]'))[0].get('issuer', '') if 'identities' in user_attributes else '',
                        'federatedDateCreated': json.loads(user_attributes.get('identities', '[]'))[0].get('dateCreated', '') if 'identities' in user_attributes else ''
                    },
                    'ConditionExpression': 'attribute_not_exists(PK) OR attribute_not_exists(SK)'
                }
            })
            
            # Optional: Create additional user-related items
            if not existing_user:
                transaction_items.append({
                    'Put': {
                        'TableName': users_table.name,
                        'Item': {
                            'PK': f"USER#{user_id}",
                            'SK': "SETTINGS",
                            'entityType': 'SETTINGS',
                            'notifications': {
                                'email': True,
                                'push': False,
                                'marketing': False
                            },
                            'preferences': {
                                'theme': 'light',
                                'language': user_attributes.get('locale', 'en-US').split('-')[0],
                                'timezone': 'UTC'
                            },
                            'createdAt': timestamp,
                            'updatedAt': timestamp
                        }
                    }
                })
            
            # Execute the transaction (all operations succeed or all fail)
            logger.info(f"Executing DynamoDB transaction with {len(transaction_items)} items")
            dynamodb_client.transact_write_items(TransactItems=transaction_items)
            logger.info(f"Successfully stored user data in DynamoDB")
            
        except Exception as e:
            logger.error(f"Error querying or updating DynamoDB: {str(e)}")
            # Don't prevent user confirmation even if we have an error
            
        return event
        
    except Exception as e:
        logger.error(f"Error in post confirmation Lambda: {str(e)}")
        # Don't prevent user confirmation even if we have an error
        return event
