import json
import os
import logging
from boto3.resource.dynamodb import Table
from boto3 import resource

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB resources - more specific import
dynamodb_resource = resource('dynamodb')
users_table = dynamodb_resource.Table(os.environ.get('USERS_TABLE_NAME', ''))

def lambda_handler(event, context):
    """
    Pre-token generation Lambda trigger for Cognito.
    Adds user_id to claims based on the authenticated identity.
    
    Example events:
    
    1. Regular email login pre-token generation event:
    {
        "version": "1",
        "triggerSource": "TokenGeneration_Authentication",
        "region": "us-east-1",
        "userPoolId": "us-east-1_aBcDeFgHi",
        "userName": "johndoe",
        "callerContext": {
            "awsSdkVersion": "aws-sdk-js-2.6.4",
            "clientId": "1abc2defghij3klmnop4qrstu"
        },
        "request": {
            "userAttributes": {
                "sub": "11112222-3333-4444-5555-666677778888",
                "email_verified": "true",
                "cognito:user_status": "CONFIRMED",
                "custom:user_id": "01HGXYZ123ABCDEFGHJKLMNOPQ",
                "email": "johndoe@example.com"
            },
            "groupConfiguration": {
                "groupsToOverride": [],
                "iamRolesToOverride": [],
                "preferredRole": null
            },
            "scopes": ["openid", "email", "profile"]
        },
        "response": {
            "claimsOverrideDetails": null
        }
    }
    
    2. Google federated login pre-token generation event:
    {
        "version": "1",
        "triggerSource": "TokenGeneration_HostedAuth",
        "region": "us-east-1",
        "userPoolId": "us-east-1_aBcDeFgHi", 
        "userName": "google_123456789",
        "callerContext": {
            "awsSdkVersion": "aws-sdk-js-2.6.4",
            "clientId": "1abc2defghij3klmnop4qrstu"
        },
        "request": {
            "userAttributes": {
                "sub": "99998888-7777-6666-5555-444433332222",
                "email_verified": "true", 
                "cognito:user_status": "EXTERNAL_PROVIDER",
                "identities": "[{\"userId\":\"123456789\",\"providerName\":\"Google\",\"providerType\":\"Google\",\"issuer\":null,\"primary\":true,\"dateCreated\":1612345678}]",
                "email": "johndoe@gmail.com"
            },
            "groupConfiguration": {
                "groupsToOverride": [],
                "iamRolesToOverride": [],
                "preferredRole": null
            },
            "scopes": ["openid", "email", "profile"]
        },
        "response": {
            "claimsOverrideDetails": null
        }
    }
    """
    try:
        # Log the trigger source and user information
        trigger_source = event.get('triggerSource', 'Unknown')
        username = event.get('userName', 'Unknown')
        user_pool_id = event.get('userPoolId', 'Unknown')
        
        logger.info(f"Pre-token generation event received - Source: {trigger_source}, User: {username}, Pool: {user_pool_id}")
        
        # Get Cognito sub from the event
        user_attributes = event.get('request', {}).get('userAttributes', {})
        cognito_sub = user_attributes.get('sub')
        
        if not cognito_sub:
            logger.error("No sub found in user attributes")
            return event
        
        # Initialize response structure if needed
        if 'claimsOverrideDetails' not in event['response']:
            event['response']['claimsOverrideDetails'] = {}
            
        if 'claimsToAddOrOverride' not in event['response'].get('claimsOverrideDetails', {}):
            if event['response']['claimsOverrideDetails'] is None:
                event['response']['claimsOverrideDetails'] = {}
                
            event['response']['claimsOverrideDetails']['claimsToAddOrOverride'] = {}
            
        # ---------------------------------------------------------------------
        # FLOW 1: User ID from Cognito attributes (most common case)
        # - Checks if custom:user_id exists in the user attributes
        # - This is the fastest path requiring no database lookup
        # - Happens for most logins after initial setup
        # ---------------------------------------------------------------------
        if 'custom:user_id' in user_attributes:
            user_id = user_attributes['custom:user_id']
            logger.info(f"Found custom:user_id in user attributes: {user_id}")
            
            # Add to token claims (using clean name without 'custom:' prefix)
            event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['user_id'] = user_id
            
            # ---------------------------------------------------------------------
            # OPTIONAL: Token enrichment with additional user data
            # - Gets user profile and settings to enhance token
            # - Adds business-relevant claims to the token
            # - Improves performance by reducing separate lookups in services
            # ---------------------------------------------------------------------
            try:
                # Get user profile info using direct GetItem operation
                # - PK = "USER#{user_id}" (partition key)
                # - SK = "PROFILE" (sort key)
                user_profile = users_table.get_item(
                    Key={
                        'PK': f"USER#{user_id}",
                        'SK': "PROFILE"
                    }
                ).get('Item', {})
                
                if user_profile:
                    # Add user role or permissions if available
                    if 'role' in user_profile:
                        event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['role'] = user_profile['role']
                    
                    # Add account type/tier if available
                    if 'accountTier' in user_profile:
                        event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['account_tier'] = user_profile['accountTier']
                    
                    # Add signup method
                    if 'signupMethod' in user_profile:
                        event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['signup_method'] = user_profile['signupMethod']
                
                # Get user settings with another GetItem operation
                user_settings = users_table.get_item(
                    Key={
                        'PK': f"USER#{user_id}",
                        'SK': "SETTINGS"
                    }
                ).get('Item', {})
                
                if user_settings and 'preferences' in user_settings:
                    # Add language preference to token
                    if 'language' in user_settings['preferences']:
                        event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['preferred_language'] = user_settings['preferences']['language']
                    
            except Exception as e:
                logger.warning(f"Error enriching token with additional claims: {str(e)}")
            
            return event
        
        # ---------------------------------------------------------------------
        # FLOW 2: Lookup user ID by Cognito sub (fallback path)
        # - Used when custom:user_id is not in attributes
        # - Common with some federated logins or token refresh
        # - Uses GSI2 to find user_id based on Cognito identity
        # ---------------------------------------------------------------------
        logger.info(f"No user_id in attributes, looking up by Cognito sub: {cognito_sub}")
        try:
            # DynamoDB QUERY: Find user_id by Cognito sub
            # - Uses GSI2 (Global Secondary Index)
            # - GSI2PK = "IDENT#{cognito_sub}" is the partition key
            # - GSI2SK contains "USER#{user_id}" which we extract
            # - This design enables efficient identity-to-user lookup
            response = users_table.query(
                IndexName="GSI2",
                KeyConditionExpression="GSI2PK = :id",
                ExpressionAttributeValues={
                    ":id": f"IDENT#{cognito_sub}"
                }
            )
            
            if response.get('Items') and len(response['Items']) > 0:
                # Extract user_id from GSI2SK by removing the "USER#" prefix
                user_id = response['Items'][0]['GSI2SK'].replace("USER#", "")
                logger.info(f"Found user_id {user_id} for Cognito sub {cognito_sub}")
                
                # Add to token claims
                event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['user_id'] = user_id
                
                # Add authentication context to claims
                auth_type = "password"
                if trigger_source == "TokenGeneration_HostedAuth":
                    auth_type = "federated"
                elif trigger_source == "TokenGeneration_RefreshTokens":
                    auth_type = "refresh"
                
                event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['auth_type'] = auth_type
                
                # Add additional context claims as needed
                # import time
                # event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['custom_iat'] = int(time.time())
                
            else:
                logger.warning(f"No user_id found for Cognito sub {cognito_sub}")
        except Exception as e:
            logger.error(f"Error querying DynamoDB: {str(e)}")
            
        return event
        
    except Exception as e:
        logger.error(f"Error in pre token generation Lambda: {str(e)}")
        return event
