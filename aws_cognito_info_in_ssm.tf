resource "aws_ssm_parameter" "cognito_user_pool_client_main_client_id" {
  name        = "/auth/cognito_user_pool_client/main/client_id"
  value       = aws_cognito_user_pool_client.main.id
  description = "Cognito User Pool Main Client - Client Id"
  type        = "String"
}

resource "aws_ssm_parameter" "cognito_user_pool_client_main_client_secrets" {
  name        = "/auth/cognito_user_pool_client/main/client_secret"
  value       = aws_cognito_user_pool_client.main.client_secret
  description = "Cognito User Pool Main Client - Client Secret - ${aws_cognito_user_pool_client.main.id}"
  type        = "SecureString"
}

# SSM Parameters for secrets
# resource "aws_ssm_parameter" "github_client_id" {
#   name  = "/${var.environment}/auth/github_client_id"
#   type  = "SecureString"
#   value = "placeholder" # Replace via AWS Console or CI/CD
#
#   lifecycle {
#     ignore_changes = [value]
#   }
# }
#
# resource "aws_ssm_parameter" "github_client_secret" {
#   name  = "/${var.environment}/auth/github_client_secret"
#   type  = "SecureString"
#   value = "placeholder" # Replace via AWS Console or CI/CD
#
#   lifecycle {
#     ignore_changes = [value]
#   }
# }
#
# resource "aws_ssm_parameter" "google_client_id" {
#   name  = "/${var.environment}/auth/google_client_id"
#   type  = "SecureString"
#   value = "placeholder" # Replace via AWS Console or CI/CD
#
#   lifecycle {
#     ignore_changes = [value]
#   }
# }
#
# resource "aws_ssm_parameter" "google_client_secret" {
#   name  = "/${var.environment}/auth/google_client_secret"
#   type  = "SecureString"
#   value = "placeholder" # Replace via AWS Console or CI/CD
#
#   lifecycle {
#     ignore_changes = [value]
#   }
# }