module "lambda_trigger_post_confirmation" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.20.1"

  function_name                     = "${var.domain_name}-post-confirmation"
  description                       = "Lambda function to set user_id after confirmation and store user data"
  handler                           = "index.lambda_handler"
  runtime                           = "python3.13"
  timeout                           = 30
  role_name                         = "lambda-role-${var.domain_name}-post-confirmation-${local.region}"
  cloudwatch_logs_retention_in_days = 14

  source_path = [
    {
      path             = "${path.module}/src/post_confirmation_lambda"
      pip_requirements = true
      # Using default pip
    }
  ]

  environment_variables = {
    USERS_TABLE_NAME = module.users_table.dynamodb_table_id
  }

  attach_policy_statements = true
  policy_statements = {
    cognito_access = {
      effect = "Allow",
      actions = [
        "cognito-idp:AdminUpdateUserAttributes",
      ],
      resources = [aws_cognito_user_pool.main.arn]
    },
    dynamodb_access = {
      effect = "Allow",
      actions = [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:TransactWriteItems"
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
