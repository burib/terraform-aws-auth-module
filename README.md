# terraform-aws-module-template

## github template to start writing versioned terraform module

```terraform

module "auth" {
  source = "github.com/burib/terraform-aws-auth-module?ref=init"

  domain_name     = "example.com"
  environment     = var.environment
  route53_zone_id = "ZXXXXXXXX"
```
