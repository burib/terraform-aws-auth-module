locals {
  region          = data.aws_region.current.name
  auth_domain     = "${var.auth_domain}.${var.domain_name}"
  password_policy = var.password_policy

  auth_urls = {
    callback = "/auth/callback"
    logout   = "/auth/logout"
    error    = "/auth/error.html"
  }
  sanitized_domain_name = replace(var.domain_name, ".", "-")
  _domain_parts         = split(".", var.domain_name)
  _processed_domain_parts = length(local._domain_parts) == 0 || local._domain_parts[0] == "" ? [] : concat(
    # First part (lowercase)
    [lower(local._domain_parts[0])],
    # Subsequent parts ("Dot" + TitleCase)
    [for i, part in local._domain_parts : format("Dot%s", title(part)) if i > 0]
  )

  # Join the processed parts
  camel_case_domain_name = join("", local._processed_domain_parts)

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