# Variables
variable "domain_name" {
  type        = string
  description = "Main domain name (e.g., example.com)"
}

variable "password_policy" {
  type = object({
    minimum_length                   = number
    require_lowercase                = bool
    require_numbers                  = bool
    require_symbols                  = bool
    require_uppercase                = bool
    temporary_password_validity_days = number
  })
  description = "Password policy for the user pool"
  default = {
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }
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

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}

variable "alert_email" {
  type        = string
  description = "Email address for receiving alerts"
  default     = ""
}

variable "auth_domain" {
  type        = string
  description = "Auth domain name (e.g., auth.example.com)"
  default     = "auth"
}

