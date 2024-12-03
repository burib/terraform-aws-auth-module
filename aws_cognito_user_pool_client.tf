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
