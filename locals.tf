locals {
  region      = data.aws_region.current.name
  auth_domain = "${var.auth_domain}.${var.domain_name}"
  sanitized_domain_name = replace(var.domain_name, ".", "-")

  password_policy = var.password_policy

  auth_urls = {
    callback = "/auth/callback"
    logout   = "/auth/logout"
    error    = "/auth/error.html"
  }

  # Social provider configurations
  # social_providers = {
  #   github = {
  #     client_id     = aws_ssm_parameter.github_client_id.value
  #     client_secret = aws_ssm_parameter.github_client_secret.value
  #     scopes        = ["email", "profile", "openid"]
  #   }
  #   google = {
  #     client_id     = aws_ssm_parameter.google_client_id.value
  #     client_secret = aws_ssm_parameter.google_client_secret.value
  #     scopes        = ["email", "profile", "openid"]
  #   }
  # }
}
