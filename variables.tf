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

# Multi-tenant configuration
variable "tenant_strategy" {
  type        = string
  description = "Strategy for determining tenant ID for new users: 'domain' (use email domain), 'invitation' (require invitation), 'personal' (create personal tenant), 'strict' (require explicit tenant)"
  default     = "domain"
  validation {
    condition     = contains(["domain", "invitation", "personal", "strict"], var.tenant_strategy)
    error_message = "tenant_strategy must be one of: domain, invitation, personal, strict"
  }
}

variable "allow_personal_tenants" {
  type        = bool
  description = "Whether to allow creation of personal tenants if no organizational tenant can be determined"
  default     = true
}

variable "domain_tenant_map" {
  type        = map(string)
  description = "Mapping of email domains to tenant IDs (e.g., {'example.com': 'example', 'sub.example.com': 'example'})"
  default     = {}
}

variable "allowed_domains" {
  type        = list(string)
  description = "List of allowed email domains for registration. If empty, all domains are allowed."
  default     = []
}

variable "require_tenant" {
  type        = bool
  description = "Whether to require a valid tenant ID during registration (fails registration if tenant cannot be determined)"
  default     = false
}

# Registration control
variable "allow_admin_create_user_only" {
  type        = bool
  description = "Whether to restrict user creation to administrators only. When true, self-signup is disabled and only admins can create users."
  default     = false
}
