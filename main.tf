# Variables
variable "domain_name" {
  type        = string
  description = "Main domain name (e.g., example.com)"
}

variable "wildcard_certificate_arn" {
  type        = string
  description = "ARN of the ACM certificate to use for CloudFront"
}

variable "environment" {
  description = <<EOF
      Environment variable used to tag resources created by this module.

      **Example values are:**
        - temp
        - dev
        - staging
        - prod

      **Notes:**
        Put here your notes if there is any.
  EOF
  type        = string
}

variable "route53_zone_id" {
  type        = string
  description = "Route53 zone ID for DNS records"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}

variable "alert_email" {
  type        = string
  description = "Email address for receiving alerts"
  default     = ""
}

# Locals
locals {
  auth_domain = "auth.${var.domain_name}"
  api_domain  = "api.${var.domain_name}"
  
  password_policy = {
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  # Social provider configurations
  social_providers = {
    github = {
      client_id     = aws_ssm_parameter.github_client_id.value
      client_secret = aws_ssm_parameter.github_client_secret.value
      scopes        = ["email", "profile", "openid"]
    }
    google = {
      client_id     = aws_ssm_parameter.google_client_id.value
      client_secret = aws_ssm_parameter.google_client_secret.value
      scopes        = ["email", "profile", "openid"]
    }
  }
}

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

# SSM Parameters for secrets
resource "aws_ssm_parameter" "github_client_id" {
  name  = "/${var.environment}/auth/github_client_id"
  type  = "SecureString"
  value = "placeholder" # Replace via AWS Console or CI/CD

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "github_client_secret" {
  name  = "/${var.environment}/auth/github_client_secret"
  type  = "SecureString"
  value = "placeholder" # Replace via AWS Console or CI/CD

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "google_client_id" {
  name  = "/${var.environment}/auth/google_client_id"
  type  = "SecureString"
  value = "placeholder" # Replace via AWS Console or CI/CD

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "google_client_secret" {
  name  = "/${var.environment}/auth/google_client_secret"
  type  = "SecureString"
  value = "placeholder" # Replace via AWS Console or CI/CD

  lifecycle {
    ignore_changes = [value]
  }
}

# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${var.domain_name}-${var.environment}"

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
    recovery_mechanism {
      name     = "verified_phone_number"
      priority = 2
    }
  }

  # MFA Configuration
  mfa_configuration = "OPTIONAL"
  
  software_token_mfa_configuration {
    enabled = true
  }

  # Password Policy
  password_policy {
    minimum_length                   = local.password_policy.minimum_length
    require_lowercase                = local.password_policy.require_lowercase
    require_numbers                  = local.password_policy.require_numbers
    require_symbols                  = local.password_policy.require_symbols
    require_uppercase                = local.password_policy.require_uppercase
    temporary_password_validity_days = local.password_policy.temporary_password_validity_days
  }

  # Email Configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # User Attributes
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable            = true

    string_attribute_constraints {
      min_length = 3
      max_length = 255
    }
  }

  schema {
    name                = "custom:role"
    attribute_data_type = "String"
    required            = false
    mutable            = true

    string_attribute_constraints {
      min_length = 1
      max_length = 255
    }
  }

  # Device Configuration
  device_configuration {
    challenge_required_on_new_device      = true
    device_only_remembered_on_user_prompt = true
  }

  # Admin Create User Config
  admin_create_user_config {
    allow_admin_create_user_only = false
    
    invite_message_template {
      email_message = "Your username is {username} and temporary password is {####}."
      email_subject = "Your temporary password for ${var.domain_name}"
      sms_message   = "Your username is {username} and temporary password is {####}."
    }
  }

  # User Pool Add-ons
  user_pool_add_ons {
    advanced_security_mode = "ENFORCED"
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = var.tags
}

# GitHub Identity Provider
resource "aws_cognito_identity_provider" "github" {
  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "GitHub"
  provider_type = "OIDC"

  provider_details = {
    client_id                = aws_ssm_parameter.github_client_id.value
    client_secret            = aws_ssm_parameter.github_client_secret.value
    attributes_request_method = "GET"
    oidc_issuer             = "https://github.com"
    authorize_scopes        = "openid email profile"
    authorize_url          = "https://github.com/login/oauth/authorize"
    token_url             = "https://github.com/login/oauth/access_token"
    attributes_url        = "https://api.github.com/user"
    jwks_uri             = "https://token.actions.githubusercontent.com/.well-known/jwks"
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
    name     = "name"
    given_name = "name"
    picture  = "avatar_url"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Google Identity Provider
resource "aws_cognito_identity_provider" "google" {
  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    client_id     = aws_ssm_parameter.google_client_id.value
    client_secret = aws_ssm_parameter.google_client_secret.value
    authorize_scopes = "email profile openid"
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
    given_name = "given_name"
    family_name = "family_name"
    picture = "picture"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "main" {
  domain          = local.auth_domain
  certificate_arn = var.wildcard_certificate_arn
  user_pool_id    = aws_cognito_user_pool.main.id

  lifecycle {
    create_before_destroy = true
    replace_triggered_by = [
      aws_cognito_user_pool.main.id
    ]
  }
}

# Cognito Identity Pool
resource "aws_cognito_identity_pool" "main" {
  identity_pool_name = "${var.domain_name}-${var.environment}"
  
  allow_unauthenticated_identities = false
  allow_classic_flow              = false

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.main.id
    provider_name          = aws_cognito_user_pool.main.endpoint
    server_side_token_check = false
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = var.tags
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "main" {
  name                                 = "${var.domain_name}-client"
  user_pool_id                        = aws_cognito_user_pool.main.id
  
  generate_secret                     = true
  prevent_user_existence_errors       = "ENABLED"
  refresh_token_validity              = 30
  access_token_validity               = 1
  id_token_validity                   = 1
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  
  supported_identity_providers         = ["COGNITO", "Google", "GitHub"]
  
  callback_urls = [
    "https://${var.domain_name}/callback",
    "https://${var.domain_name}/signin"
  ]
  
  logout_urls = [
    "https://${var.domain_name}/signout",
    "https://${var.domain_name}/logout"
  ]

  token_validity_units {
    access_token  = "hours"
    id_token     = "hours"
    refresh_token = "days"
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_cognito_identity_provider.github,
    aws_cognito_identity_provider.google
  ]
}

# Route53 Records for Auth Domain
resource "aws_route53_record" "auth_domain" {
  zone_id = var.route53_zone_id
  name    = local.auth_domain
  type    = "A"

  alias {
    name                   = aws_cognito_user_pool_domain.main.cloudfront_distribution_arn
    zone_id                = aws_cognito_user_pool_domain.main.cloudfront_distribution_zone_id
    evaluate_target_health = false
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "auth_domain_ipv6" {
  zone_id = var.route53_zone_id
  name    = local.auth_domain
  type    = "AAAA"

  alias {
    name                   = aws_cognito_user_pool_domain.main.cloudfront_distribution_arn
    zone_id                = aws_cognito_user_pool_domain.main.cloudfront_distribution_zone_id
    evaluate_target_health = false
  }

  lifecycle {
    create_before_destroy = true
  }
}

# CloudWatch Metrics and Alarms
resource "aws_cloudwatch_metric_alarm" "auth_errors" {
  count = var.alert_email != "" ? 1 : 0
  
  alarm_name          = "${var.domain_name}-auth-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Cognito"
  period             = "300"
  statistic          = "Sum"
  threshold          = "10"
  alarm_description  = "Authentication errors exceeded threshold"
  alarm_actions      = [aws_sns_topic.auth_alerts[0].arn]

  dimensions = {
    UserPool = aws_cognito_user_pool.main.id
  }

  tags = var.tags
}

# SNS Topic for Alerts
resource "aws_sns_topic" "auth_alerts" {
  count = var.alert_email != "" ? 1 : 0
  
  name = "${var.domain_name}-auth-alerts"
  tags = var.tags
}

resource "aws_sns_topic_subscription" "auth_alerts_email" {
  count = var.alert_email != "" ? 1 : 0
  
  topic_arn = aws_sns_topic.auth_alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Outputs
output "user_pool_id" {
  value       = aws_cognito_user_pool.main.id
  description = "The ID of the Cognito User Pool"
}

output "user_pool_client_id" {
  value       = aws_cognito_user_pool_
