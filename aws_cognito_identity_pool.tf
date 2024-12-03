# Cognito Identity Pool
resource "aws_cognito_identity_pool" "main" {
  identity_pool_name = "${var.domain_name}-${var.environment}"

  allow_unauthenticated_identities = false
  allow_classic_flow               = false

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.main.id
    provider_name           = aws_cognito_user_pool.main.endpoint
    server_side_token_check = false
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = var.tags
}