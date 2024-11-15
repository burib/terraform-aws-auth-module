output "environment" {
  value       = var.environment
  description = "Environment where this stack has been deployed to."
}

output "region" {
  value       = local.region
  description = "AWS Region code where this stack has been deployed to."
}

output "account_id" {
  value       = local.account_id
  description = "AWS Account ID where this stack has been deployed to."
}
