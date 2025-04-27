import json
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Pre Sign-Up Lambda trigger for Cognito.
    
    This function can be used to validate user signups based on tenant strategy
    configuration or other rules. Currently, it just passes through the event.
    
    You can extend this function to implement custom signup validation logic:
    - Domain validation
    - Custom attribute validation
    - Tenant-specific signup rules
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Extract information from the event for potential validation
    user_attributes = event.get('request', {}).get('userAttributes', {})
    client_metadata = event.get('request', {}).get('clientMetadata', {})
    username = event.get('userName', '')
    email = user_attributes.get('email', '')
    
    # Get configuration from environment variables
    tenant_strategy = os.environ.get('TENANT_STRATEGY', 'domain')
    allowed_domains = json.loads(os.environ.get('ALLOWED_DOMAINS', '[]'))
    
    # Implement domain validation if configured
    if allowed_domains and tenant_strategy in ['domain', 'strict']:
        if email and '@' in email:
            domain = email.split('@')[1].lower()
            if domain not in allowed_domains:
                logger.warning(f"Email domain {domain} not in allowed domains list: {allowed_domains}")
                raise Exception(f"Email domain {domain} is not allowed for registration")
    
    # Pass through the event after validation
    logger.info(f"Pre-signup validation passed for {username}")
    return event