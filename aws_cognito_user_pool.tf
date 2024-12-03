resource "aws_cognito_user_pool" "main" {
  name = var.domain_name

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
    email_sending_account = "COGNITO_DEFAULT" # Or use "DEVELOPER" with SES
    # from_email_address    = "no-reply@${var.domain_name}"  # Optional when using COGNITO_DEFAULT
  }

  # Configure auto verification and messages
  auto_verified_attributes = ["email"]

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
    name                = "custom:role"
    attribute_data_type = "String"
    required            = false
    mutable             = true

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