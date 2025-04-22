resource "aws_cognito_user_pool" "main" {
  name                     = var.domain_name
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

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
    minimum_length                   = var.password_policy.minimum_length
    require_lowercase                = var.password_policy.require_lowercase
    require_numbers                  = var.password_policy.require_numbers
    require_symbols                  = var.password_policy.require_symbols
    require_uppercase                = var.password_policy.require_uppercase
    temporary_password_validity_days = var.password_policy.temporary_password_validity_days
  }

  # Email Configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT" # Or use "DEVELOPER" with SES
    # from_email_address    = "no-reply@${var.domain_name}"  # Optional when using COGNITO_DEFAULT
  }

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "${var.domain_name} - verification code."
    email_message        = "Thank you for signing up! Your verification code is {####}"
  }

  # User Attributes
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 3
      max_length = 255
    }
  }

  schema {
    name                = "role"
    attribute_data_type = "String"
    required            = false
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 255
    }
  }

  schema {
    name                = "user_id"
    attribute_data_type = "String"
    required            = true
    mutable             = true
    string_attribute_constraints {
      min_length = 36 # UUID length
      max_length = 36
    }
  }

  # Add the lambda triggers
  lambda_config {
    post_confirmation    = module.lambda_trigger_post_confirmation.lambda_function_arn
    pre_token_generation = module.lambda_trigger_pre_token_generation.lambda_function_arn
    pre_sign_up          = module.lambda_trigger_pre_signup.lambda_function_arn
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

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.domain_name}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret                      = true
  prevent_user_existence_errors        = "ENABLED"
  refresh_token_validity               = 30
  access_token_validity                = 1
  id_token_validity                    = 1
  enable_token_revocation              = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]

  supported_identity_providers = ["COGNITO"]
  # supported_identity_providers = ["COGNITO", "Google", "GitHub"]

  callback_urls = [
    "https://${var.domain_name}${local.auth_urls.callback}"
  ]

  logout_urls = [
    "https://${var.domain_name}${local.auth_urls.logout}"
  ]

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  lifecycle {
    create_before_destroy = true
  }

  # depends_on = [
  #   aws_cognito_identity_provider.github,
  #   aws_cognito_identity_provider.google
  # ]
}
