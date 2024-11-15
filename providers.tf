terraform {
  required_version = "~> 1.0" # allow only 1.x versions.

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0" # minimum 5.x is required to be able to use this module
    }
  }
}
