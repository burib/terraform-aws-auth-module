module "lambda_trigger_pre_token_generation" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.20.1"

  function_name                     = "${var.domain_name}-pre-token-generation"
  description                       = "Lambda function to add user_id to Cognito tokens"
  handler                           = "index.lambda_handler"
  runtime                           = "python3.13"
  timeout                           = 5
  role_name                         = "lambda-role-${var.domain_name}-pre-token-generation-${local.region}"
  cloudwatch_logs_retention_in_days = 14

  source_path = [
    {
      path             = "${path.module}/src/pre_token_generation_lambda"
      pip_requirements = true
    }
  ]

  environment_variables = {
    USERS_TABLE_NAME = module.users_table.dynamodb_table_id
  }

  attach_policy_statements = true
  policy_statements = {
    dynamodb_access = {
      effect = "Allow",
      actions = [
        "dynamodb:GetItem",
        "dynamodb:Query"
      ],
      resources = [
        module.users_table.dynamodb_table_arn,
        "${module.users_table.dynamodb_table_arn}/index/*"
      ]
    }
  }

  allowed_triggers = {
    cognito = {
      principal  = "cognito-idp.amazonaws.com"
      source_arn = aws_cognito_user_pool.main.arn
    }
  }

  tags = var.tags
}
