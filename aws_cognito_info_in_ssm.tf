resource "aws_ssm_parameter" "cognito_user_pool_arn" {
  name        = "/auth/cognito/user_pool_arn"
  value       = aws_cognito_user_pool.main.arn
  description = "Cognito User Pool ARN"
  type        = "String"
}

resource "aws_ssm_parameter" "cognito_user_pool_id" {
  name        = "/auth/cognito/user_pool_id"
  value       = aws_cognito_user_pool.main.id
  description = "Cognito User Pool ID"
  type        = "String"
}

resource "aws_ssm_parameter" "cognito_user_pool_client_main_client_id" {
  name        = "/auth/cognito/user_pool_client_id"
  value       = aws_cognito_user_pool_client.main.id
  description = "Cognito User Pool Main Client - Client Id"
  type        = "String"
}

resource "aws_ssm_parameter" "cognito_user_pool_client_main_client_secrets" {
  name        = "/auth/cognito/user_pool_client_secret"
  value       = aws_cognito_user_pool_client.main.client_secret
  description = "Cognito User Pool Main Client - Client Secret - ${aws_cognito_user_pool_client.main.id}"
  type        = "SecureString"
}

resource "aws_ssm_parameter" "cognito_ui_logout_url" {
  name        = "/auth/cognito/ui_logout_url"
  value       = "TODO"
  description = "UI Logout Page - TODO"
  type        = "String"
}

resource "aws_ssm_parameter" "cognito_ui_refresh_url" {
  name        = "/auth/cognito/ui_refresh_url"
  value       = "TODO"
  description = "UI Refresh Token Page - TODO"
  type        = "String"
}

# function render_ui_config() {
#  local LOGIN_URL=$(get_ssm_value "/auth/cognito/ui_login_url")
#  local LOGOUT_URL=$(get_ssm_value "/auth/cognito/ui_logout_url")
#  local REFRESH_URL=$(get_ssm_value "/auth/cognito/ui_refresh_url")
#  cat "$CONFIG_DIR/config.json" | jq '.login_url = "$LOGIN_URL" | .logout_url = "$LOGOUT_URL"' | jq -c > "${DIST_DIR}/config.json"

#  cat "$DIST_DIR/config.json" | jq
# }

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
