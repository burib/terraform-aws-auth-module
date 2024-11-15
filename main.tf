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

  tags = var.tags
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "main" {
  domain          = local.auth_domain
  certificate_arn = var.wildcard_certificate_arn
  user_pool_id    = aws_cognito_user_pool.main.id
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

  depends_on = [
    aws_cognito_user_pool_identity_provider.github,
    aws_cognito_user_pool_identity_provider.google
  ]
}

# DynamoDB Table for Cedar Policies
resource "aws_dynamodb_table" "cedar_policies" {
  name           = "${var.domain_name}-cedar-policies"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "policy_id"
  range_key      = "version"

  attribute {
    name = "policy_id"
    type = "S"
  }

  attribute {
    name = "version"
    type = "N"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = var.tags
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
}

# Outputs
output "user_pool_id" {
  value       = aws_cognito_user_pool.main.id
  description = "The ID of the Cognito User Pool"
}

output "user_pool_client_id" {
  value       = aws_cognito_user_pool_client.main.id
  description = "The ID of the Cognito User Pool Client"
}

output "identity_pool_id" {
  value       = aws_cognito_identity_pool.main.id
  description = "The ID of the Cognito Identity Pool"
}

output "auth_domain" {
  value       = local.auth_domain
  description = "The domain name for the authentication endpoint"
}
