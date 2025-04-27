# DynamoDB Query Examples for Multi-Tenant Auth Module

This document provides ready-to-use AWS CLI commands for common query patterns with the multi-tenant authentication module. Replace placeholder values in `<brackets>` with your actual values.

## Prerequisites

For these queries, you'll need:

1. The DynamoDB table name (referred to as `<table_name>` below)
2. AWS CLI configured with appropriate permissions
3. Tenant IDs, user IDs, or other relevant values depending on the query

## Query Examples

### 1. Find User by Cognito Sub

Find which user and tenant a Cognito identity belongs to:

```bash
aws dynamodb query \
    --table-name <table_name> \
    --index-name GSI2 \
    --key-condition-expression "GSI2PK = :id" \
    --expression-attribute-values '{":id": {"S": "IDENT#<cognito_sub>"}}' \
    --region <region>
```

### 2. Get All Tenants a User Belongs To

Find all tenants that a specific user is a member of:

```bash
aws dynamodb query \
    --table-name <table_name> \
    --key-condition-expression "PK = :userId AND begins_with(SK, :tenantPrefix)" \
    --expression-attribute-values '{":userId": {"S": "USER#<user_id>"}, ":tenantPrefix": {"S": "TENANT#"}}' \
    --region <region>
```

### 3. Get All Users in a Tenant

Find all users in a specific tenant (using GSI3):

```bash
aws dynamodb query \
    --table-name <table_name> \
    --index-name GSI3 \
    --key-condition-expression "GSI3PK = :tenantId AND begins_with(GSI3SK, :userPrefix)" \
    --expression-attribute-values '{":tenantId": {"S": "TENANT#<tenant_id>"}, ":userPrefix": {"S": "USER#"}}' \
    --region <region>
```

### 4. Get User Profile in a Specific Tenant

Get a user's profile in a specific tenant:

```bash
aws dynamodb get-item \
    --table-name <table_name> \
    --key '{"PK": {"S": "TENANT#<tenant_id>#USER#<user_id>"}, "SK": {"S": "PROFILE"}}' \
    --region <region>
```

### 5. Check if User Belongs to a Specific Tenant

Verify if a user is a member of a specific tenant:

```bash
aws dynamodb get-item \
    --table-name <table_name> \
    --key '{"PK": {"S": "USER#<user_id>"}, "SK": {"S": "TENANT#<tenant_id>"}}' \
    --region <region>
```

### 6. Get All User Settings in a Tenant

Get a user's settings in a specific tenant:

```bash
aws dynamodb get-item \
    --table-name <table_name> \
    --key '{"PK": {"S": "TENANT#<tenant_id>#USER#<user_id>"}, "SK": {"S": "SETTINGS"}}' \
    --region <region>
```

### 7. Get All Identities for a User in a Tenant

Get all login methods (identities) for a user in a specific tenant:

```bash
aws dynamodb query \
    --table-name <table_name> \
    --key-condition-expression "PK = :pk AND begins_with(SK, :identityPrefix)" \
    --expression-attribute-values '{":pk": {"S": "TENANT#<tenant_id>#USER#<user_id>"}, ":identityPrefix": {"S": "IDENTITY#"}}' \
    --region <region>
```

### 8. Get All Users With Admin Role in a Tenant

Find all users with an admin role in a specific tenant:

```bash
aws dynamodb query \
    --table-name <table_name> \
    --key-condition-expression "PK = :user_prefix AND SK = :tenant_id" \
    --filter-expression "role = :role" \
    --expression-attribute-values '{
        ":user_prefix": {"S": "USER#"},
        ":tenant_id": {"S": "TENANT#<tenant_id>"},
        ":role": {"S": "admin"}
    }' \
    --region <region>
```

### 9. Update User Role in a Tenant

Update a user's role in a specific tenant:

```bash
aws dynamodb update-item \
    --table-name <table_name> \
    --key '{"PK": {"S": "USER#<user_id>"}, "SK": {"S": "TENANT#<tenant_id>"}}' \
    --update-expression "SET #role = :newRole, updatedAt = :timestamp" \
    --expression-attribute-names '{"#role": "role"}' \
    --expression-attribute-values '{":newRole": {"S": "admin"}, ":timestamp": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"}}' \
    --region <region>
```

### 10. Add User to a New Tenant

Add an existing user to another tenant:

```bash
aws dynamodb put-item \
    --table-name <table_name> \
    --item '{
        "PK": {"S": "USER#<user_id>"},
        "SK": {"S": "TENANT#<tenant_id>"},
        "status": {"S": "ACTIVE"},
        "role": {"S": "member"},
        "joinedAt": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
        "tenantId": {"S": "<tenant_id>"},
        "GSI4PK": {"S": "USER#<user_id>"},
        "GSI4SK": {"S": "TENANT#<tenant_id>"}
    }' \
    --region <region>
```

### 11. Initialize User Profile and Settings in a New Tenant

After adding a user to a new tenant, initialize their profile and settings:

```bash
# Create profile
aws dynamodb put-item \
    --table-name <table_name> \
    --item '{
        "PK": {"S": "TENANT#<tenant_id>#USER#<user_id>"},
        "SK": {"S": "PROFILE"},
        "userId": {"S": "<user_id>"},
        "tenantId": {"S": "<tenant_id>"},
        "status": {"S": "ACTIVE"},
        "createdAt": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
        "updatedAt": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
        "entityType": {"S": "USER"},
        "GSI3PK": {"S": "TENANT#<tenant_id>"},
        "GSI3SK": {"S": "USER#<user_id>"}
    }' \
    --region <region>

# Create settings
aws dynamodb put-item \
    --table-name <table_name> \
    --item '{
        "PK": {"S": "TENANT#<tenant_id>#USER#<user_id>"},
        "SK": {"S": "SETTINGS"},
        "entityType": {"S": "SETTINGS"},
        "tenantId": {"S": "<tenant_id>"},
        "createdAt": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
        "updatedAt": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
        "preferences": {"M": {
            "theme": {"S": "light"},
            "language": {"S": "en"}
        }},
        "GSI3PK": {"S": "TENANT#<tenant_id>"},
        "GSI3SK": {"S": "USER#<user_id>"}
    }' \
    --region <region>
```

### 12. Remove User from a Tenant

Remove a user's membership from a tenant:

```bash
aws dynamodb delete-item \
    --table-name <table_name> \
    --key '{"PK": {"S": "USER#<user_id>"}, "SK": {"S": "TENANT#<tenant_id>"}}' \
    --region <region>
```

### 13. Add Group Membership for a User in a Tenant

Add a user to a group within a tenant:

```bash
aws dynamodb put-item \
    --table-name <table_name> \
    --item '{
        "PK": {"S": "TENANT#<tenant_id>#USER#<user_id>"},
        "SK": {"S": "GROUP#<group_id>"},
        "role": {"S": "member"},
        "tenantId": {"S": "<tenant_id>"},
        "groupId": {"S": "<group_id>"},
        "joinedAt": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"}
    }' \
    --region <region>
```

### 14. Get All Groups a User Belongs to in a Tenant

Get all groups that a user is a member of in a specific tenant:

```bash
aws dynamodb query \
    --table-name <table_name> \
    --key-condition-expression "PK = :pk AND begins_with(SK, :groupPrefix)" \
    --expression-attribute-values '{":pk": {"S": "TENANT#<tenant_id>#USER#<user_id>"}, ":groupPrefix": {"S": "GROUP#"}}' \
    --region <region>
```

## Using with AWS SDK

If you're using a programming language with the AWS SDK, these queries can be adapted easily. Here's an example in Node.js:

```javascript
// Find user by Cognito sub
const AWS = require('aws-sdk');
const dynamoDB = new AWS.DynamoDB.DocumentClient();

async function findUserByCognitoSub(cognitoSub) {
  const params = {
    TableName: 'your-table-name',
    IndexName: 'GSI2',
    KeyConditionExpression: 'GSI2PK = :id',
    ExpressionAttributeValues: {
      ':id': `IDENT#${cognitoSub}`
    }
  };
  
  const result = await dynamoDB.query(params).promise();
  return result.Items;
}
```

## Performance Considerations

- These queries are optimized for the table's access patterns
- For high-volume operations, consider using DynamoDB Accelerator (DAX)
- For large result sets, use pagination with `Limit` and `ExclusiveStartKey` parameters
- For analytics, consider exporting to S3 and using Athena rather than querying DynamoDB directly
