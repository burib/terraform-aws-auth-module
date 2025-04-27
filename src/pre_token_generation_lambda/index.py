import json
import os
import logging
from boto3.resource.dynamodb import Table
from boto3 import resource
from boto3.dynamodb.conditions import Key

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB resources
dynamodb_resource = resource('dynamodb')
users_table = dynamodb_resource.Table(os.environ.get('USERS_TABLE_NAME', ''))

def lambda_handler(event, context):
    """
    Pre-token generation Lambda trigger for Cognito with multi-tenant support.
    - Adds user_id and tenant_id to claims based on the authenticated identity
    - Handles users who belong to multiple tenants
    - Keeps token scoped to a single tenant per session
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
            
        # FLOW 1: User ID and Tenant ID from Cognito attributes (most common case)
        if 'custom:user_id' in user_attributes and 'custom:tenant_id' in user_attributes:
            user_id = user_attributes['custom:user_id']
            tenant_id = user_attributes['custom:tenant_id']
            
            logger.info(f"Found custom:user_id ({user_id}) and custom:tenant_id ({tenant_id}) in user attributes")
            
            # Verify tenant membership is still valid
            try:
                tenant_membership = users_table.get_item(
                    Key={
                        'PK': f"USER#{user_id}",
                        'SK': f"TENANT#{tenant_id}"
                    }
                ).get('Item', {})
                
                if not tenant_membership:
                    logger.warning(f"User {user_id} no longer belongs to tenant {tenant_id}. Checking for other tenants.")
                    
                    # Get user's available tenants
                    available_tenants = get_user_tenants(user_id)
                    
                    if not available_tenants:
                        logger.error(f"User {user_id} does not belong to any tenant.")
                        # Don't add tenant_id to token as it's not valid
                    else:
                        # Take the first available tenant
                        tenant_id = available_tenants[0]
                        logger.info(f"Using alternative tenant: {tenant_id} for user {user_id}")
                
                # Add to token claims (using clean names without 'custom:' prefix)
                event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['user_id'] = user_id
                event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['tenant_id'] = tenant_id
                
                # Add user role in this tenant if available
                if tenant_membership and 'role' in tenant_membership:
                    event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['role'] = tenant_membership['role']
                
                # Get user's tenants for potential client-side tenant switching
                tenant_count = count_user_tenants(user_id)
                if tenant_count > 1:
                    event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['has_multiple_tenants'] = 'true'
                    event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['tenant_count'] = str(tenant_count)
                
                # Optional: Add additional user data to token
                enrich_token_with_user_data(event, user_id, tenant_id)
                    
            except Exception as e:
                logger.warning(f"Error verifying tenant membership: {str(e)}")
                # Still add basic claims but skip enrichment
                event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['user_id'] = user_id
                event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['tenant_id'] = tenant_id
            
            return event
        
        # FLOW 2: Lookup user ID and tenant ID by Cognito sub (fallback path)
        logger.info(f"No user_id or tenant_id in attributes, looking up by Cognito sub: {cognito_sub}")
        try:
            # Find user_id and tenant_id by Cognito sub using GSI2
            response = users_table.query(
                IndexName="GSI2",
                KeyConditionExpression="GSI2PK = :id",
                ExpressionAttributeValues={
                    ":id": f"IDENT#{cognito_sub}"
                }
            )
            
            if response.get('Items') and len(response['Items']) > 0:
                # Extract user_id and tenant_id from GSI2SK
                # Format is: TENANT#{tenant_id}#USER#{user_id}
                gsi2_sk = response['Items'][0]['GSI2SK']
                parts = gsi2_sk.split('#')
                
                # Extract tenant_id and user_id
                tenant_id = parts[1] if len(parts) > 1 else None
                user_id = parts[3] if len(parts) > 3 else None
                
                if tenant_id and user_id:
                    logger.info(f"Found user_id {user_id} in tenant {tenant_id} for Cognito sub {cognito_sub}")
                    
                    # Add to token claims
                    event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['user_id'] = user_id
                    event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['tenant_id'] = tenant_id
                    
                    # Check if user has multiple tenants
                    tenant_count = count_user_tenants(user_id)
                    if tenant_count > 1:
                        event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['has_multiple_tenants'] = 'true'
                        event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['tenant_count'] = str(tenant_count)
                    
                    # Add authentication context to claims
                    auth_type = "password"
                    if trigger_source == "TokenGeneration_HostedAuth":
                        auth_type = "federated"
                    elif trigger_source == "TokenGeneration_RefreshTokens":
                        auth_type = "refresh"
                    
                    event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['auth_type'] = auth_type
                    
                    # Optional: Enrich token with additional user data
                    enrich_token_with_user_data(event, user_id, tenant_id)
                else:
                    logger.warning(f"Found GSI2SK but couldn't extract tenant_id and user_id: {gsi2_sk}")
            else:
                logger.warning(f"No user_id found for Cognito sub {cognito_sub}")
        except Exception as e:
            logger.error(f"Error querying DynamoDB: {str(e)}")
            
        return event
        
    except Exception as e:
        logger.error(f"Error in pre token generation Lambda: {str(e)}")
        return event

def get_user_tenants(user_id):
    """
    Get all tenants that a user belongs to.
    
    Args:
        user_id: The user's ID
        
    Returns:
        List of tenant IDs the user belongs to
    """
    try:
        response = users_table.query(
            KeyConditionExpression=Key('PK').eq(f"USER#{user_id}") & 
                                   Key('SK').begins_with("TENANT#"),
            ProjectionExpression="SK"
        )
        
        tenants = []
        for item in response.get('Items', []):
            tenant_id = item['SK'].replace('TENANT#', '')
            tenants.append(tenant_id)
            
        return tenants
    
    except Exception as e:
        logger.error(f"Error getting user tenants: {str(e)}")
        return []

def count_user_tenants(user_id):
    """
    Count how many tenants a user belongs to.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Count of tenants the user belongs to
    """
    try:
        response = users_table.query(
            KeyConditionExpression=Key('PK').eq(f"USER#{user_id}") & 
                                   Key('SK').begins_with("TENANT#"),
            Select="COUNT"
        )
        
        return response.get('Count', 0)
    
    except Exception as e:
        logger.error(f"Error counting user tenants: {str(e)}")
        return 0

def enrich_token_with_user_data(event, user_id, tenant_id):
    """
    Add additional user data to the token claims.
    
    Args:
        event: The Lambda event
        user_id: The user's ID
        tenant_id: The tenant ID
    """
    try:
        # Get user profile for the specific tenant
        user_profile = users_table.get_item(
            Key={
                'PK': f"TENANT#{tenant_id}#USER#{user_id}",
                'SK': "PROFILE"
            }
        ).get('Item', {})
        
        if user_profile:
            # Add display name if available (but not email - that's in Cognito)
            if 'displayName' in user_profile:
                event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['display_name'] = user_profile['displayName']
            
            # Add account tier if available
            if 'accountTier' in user_profile:
                event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['account_tier'] = user_profile['accountTier']
            
            # Add user groups if available (for group-based access control)
            user_groups = get_user_groups(tenant_id, user_id)
            if user_groups:
                event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['groups'] = json.dumps(user_groups)
        
        # Get user settings
        user_settings = users_table.get_item(
            Key={
                'PK': f"TENANT#{tenant_id}#USER#{user_id}",
                'SK': "SETTINGS"
            }
        ).get('Item', {})
        
        if user_settings and 'preferences' in user_settings:
            # Add language preference to token
            if 'language' in user_settings['preferences']:
                event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['preferred_language'] = user_settings['preferences']['language']
    
    except Exception as e:
        logger.warning(f"Error enriching token with additional claims: {str(e)}")

def get_user_groups(tenant_id, user_id):
    """
    Get the groups a user belongs to within a tenant.
    
    Args:
        tenant_id: The tenant ID
        user_id: The user's ID
        
    Returns:
        List of group objects with group ID and role
    """
    try:
        response = users_table.query(
            KeyConditionExpression=Key('PK').eq(f"TENANT#{tenant_id}#USER#{user_id}") & 
                                   Key('SK').begins_with("GROUP#")
        )
        
        groups = []
        for item in response.get('Items', []):
            group_id = item['SK'].replace('GROUP#', '')
            role = item.get('role', 'member')
            groups.append({
                "id": group_id,
                "role": role
            })
            
        return groups
    
    except Exception as e:
        logger.error(f"Error getting user groups: {str(e)}")
        return []