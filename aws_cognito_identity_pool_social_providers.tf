# GitHub Identity Provider
# resource "aws_cognito_identity_provider" "github" {
#   user_pool_id  = aws_cognito_user_pool.main.id
#   provider_name = "GitHub"
#   provider_type = "OIDC"
#
#   provider_details = {
#     client_id                 = aws_ssm_parameter.github_client_id.value
#     client_secret             = aws_ssm_parameter.github_client_secret.value
#     attributes_request_method = "GET"
#     oidc_issuer               = "https://github.com"
#     authorize_scopes          = "openid email profile"
#     authorize_url             = "https://github.com/login/oauth/authorize"
#     token_url                 = "https://github.com/login/oauth/access_token"
#     attributes_url            = "https://api.github.com/user"
#     jwks_uri                  = "https://token.actions.githubusercontent.com/.well-known/jwks"
#   }
#
#   attribute_mapping = {
#     email      = "email"
#     username   = "sub"
#     name       = "name"
#     given_name = "name"
#     picture    = "avatar_url"
#   }
#
#   lifecycle {
#     create_before_destroy = true
#   }
# }
#
# # Google Identity Provider
# resource "aws_cognito_identity_provider" "google" {
#   user_pool_id  = aws_cognito_user_pool.main.id
#   provider_name = "Google"
#   provider_type = "Google"
#
#   provider_details = {
#     client_id        = aws_ssm_parameter.google_client_id.value
#     client_secret    = aws_ssm_parameter.google_client_secret.value
#     authorize_scopes = "email profile openid"
#   }
#
#   attribute_mapping = {
#     email       = "email"
#     username    = "sub"
#     given_name  = "given_name"
#     family_name = "family_name"
#     picture     = "picture"
#   }
#
#   lifecycle {
#     create_before_destroy = true
#   }
# }

# Setup Instructions for OAuth Providers
#
# 1. GitHub OAuth Setup:
# =====================
# a. Go to GitHub.com -> Settings -> Developer Settings -> OAuth Apps -> New OAuth App
# b. Fill in the application details:
#    - Application name: Your App Name (e.g., "MyApp Auth")
#    - Homepage URL: https://your-domain.com
#    - Application description: (Optional) Your app description
#    - Authorization callback URL: https://auth.your-domain.com/oauth2/idpresponse
# c. After creating, you'll get Client ID and generate a Client Secret
# d. Store credentials in SSM:
#    ```bash
#    # Store GitHub Client ID
#    aws ssm put-parameter \
#        --name "/${var.environment}/auth/github_client_id" \
#        --type "SecureString" \
#        --value "your-github-client-id" \
#        --description "GitHub OAuth Client ID"
#
#    # Store GitHub Client Secret
#    aws ssm put-parameter \
#        --name "/${var.environment}/auth/github_client_secret" \
#        --type "SecureString" \
#        --value "your-github-client-secret" \
#        --description "GitHub OAuth Client Secret"
#    ```
#
# 2. Google OAuth Setup:
# =====================
# a. Go to Google Cloud Console (https://console.cloud.google.com)
# b. Create a new project or select existing one
# c. Enable the Google+ API and Identity and Access Management (IAM) API
# d. Go to APIs & Services -> Credentials -> Create Credentials -> OAuth Client ID
# e. Configure the OAuth consent screen:
#    - User Type: External
#    - App name: Your App Name
#    - User support email: Your email
#    - Developer contact information: Your email
# f. Create OAuth Client ID:
#    - Application type: Web application
#    - Name: Your App Name
#    - Authorized JavaScript origins: https://your-domain.com
#    - Authorized redirect URIs: https://auth.your-domain.com/oauth2/idpresponse
# g. Store credentials in SSM:
#    ```bash
#    # Store Google Client ID
#    aws ssm put-parameter \
#        --name "/${var.environment}/auth/google_client_id" \
#        --type "SecureString" \
#        --value "your-google-client-id" \
#        --description "Google OAuth Client ID"
#
#    # Store Google Client Secret
#    aws ssm put-parameter \
#        --name "/${var.environment}/auth/google_client_secret" \
#        --type "SecureString" \
#        --value "your-google-client-secret" \
#        --description "Google OAuth Client Secret"
#    ```