output "environment" {
  value       = var.environment
  description = "Environment where this stack has been deployed to."
}

output "region" {
  value       = local.region
  description = "AWS Region code where this stack has been deployed to."
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

output "user_pool_client_secret" {
  value       = aws_cognito_user_pool_client.main.client_secret
  description = "The Client Secret of the Cognito User Pool Client"
  sensitive   = true
}

output "identity_pool_id" {
  value       = aws_cognito_identity_pool.main.id
  description = "The ID of the Cognito Identity Pool"
}

output "auth_domain" {
  value       = local.auth_domain
  description = "The domain name for the authentication endpoint"
}

output "auth_urls" {
  value = merge(
    local.auth_urls,
    {
      oath2_token_exchange_endpoint   = "https://${local.auth_domain}/oauth2/token"
      hosted_ui_login_url             = "https://${local.auth_domain}/login?client_id=${aws_cognito_user_pool_client.main.id}&response_type=code&scope=email+openid+profile&redirect_uri=https://${var.domain_name}${local.auth_urls.callback}"
      aws_cognito_user_pool_client_id = aws_cognito_user_pool_client.main.id
    }
  )
  description = "Map of authentication URLs"
}

output "hosted_ui_login_url" {
  value       = "https://${local.auth_domain}/login?client_id=${aws_cognito_user_pool_client.main.id}&response_type=code&scope=email+openid+profile&redirect_uri=https://${var.domain_name}${local.auth_urls.callback}"
  description = "The URL for the Cognito Hosted UI"
}

output "token_signing_key_url" {
  value       = "https://cognito-idp.${local.region}.amazonaws.com/${aws_cognito_user_pool.main.id}/.well-known/jwks.json"
  description = "Token signing key URL"
}

output "token_issuer_endpoint" {
  value       = "https://cognito-idp.${local.region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
  description = "URL of the token issuer"
}
