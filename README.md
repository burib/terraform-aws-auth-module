# terraform-aws-auth-module ( beta )

## This module is used to create a cognito user pool and identity pool

```terraform

module "auth" {
  source = "github.com/burib/terraform-aws-auth-module?ref=v0"

  domain_name              = "example.com"
  environment              = "dev" # dev, staging, prod
  auth_domain              = "auth" # will be used as subdomain, e.g. auth.example.com
```
