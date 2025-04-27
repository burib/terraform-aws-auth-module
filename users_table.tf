module "users_table" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "4.2.0"

  name      = "${var.domain_name}-users"
  hash_key  = "PK"
  range_key = "SK"

  attributes = [
    {
      name = "PK"
      type = "S"
    },
    {
      name = "SK"
      type = "S"
    },
    {
      name = "GSI1PK"
      type = "S"
    },
    {
      name = "GSI1SK"
      type = "S"
    },
    {
      name = "GSI2PK"
      type = "S"
    },
    {
      name = "GSI2SK"
      type = "S"
    },
    {
      name = "GSI3PK"
      type = "S"
    },
    {
      name = "GSI3SK"
      type = "S"
    },
    {
      name = "GSI4PK"
      type = "S"
    },
    {
      name = "GSI4SK"
      type = "S"
    }
  ]

  global_secondary_indexes = [
    {
      name               = "GSI1"
      hash_key           = "GSI1PK"
      range_key          = "GSI1SK"
      projection_type    = "ALL"
      read_capacity      = null
      write_capacity     = null
      non_key_attributes = []
    },
    {
      name               = "GSI2"
      hash_key           = "GSI2PK"
      range_key          = "GSI2SK"
      projection_type    = "ALL"
      read_capacity      = null
      write_capacity     = null
      non_key_attributes = []
    },
    {
      name               = "GSI3"
      hash_key           = "GSI3PK"
      range_key          = "GSI3SK"
      projection_type    = "ALL"
      read_capacity      = null
      write_capacity     = null
      non_key_attributes = []
    },
    {
      name               = "GSI4"
      hash_key           = "GSI4PK"
      range_key          = "GSI4SK"
      projection_type    = "ALL"
      read_capacity      = null
      write_capacity     = null
      non_key_attributes = []
    }
  ]

  billing_mode   = "PAY_PER_REQUEST"
  read_capacity  = null
  write_capacity = null

  point_in_time_recovery_enabled = true

  server_side_encryption_enabled     = true
  server_side_encryption_kms_key_arn = null # Uses AWS owned CMK

  tags = var.tags
}