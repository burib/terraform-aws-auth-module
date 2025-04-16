module "lambda_trigger_pre_token_generation" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.20.1" # Use the desired version

  function_name                     = "${var.domain_name}-pre-token-generation"
  description                       = "Lambda function to add user_id to Cognito tokens"
  handler                           = "index.lambda_handler"
  runtime                           = "python3.12" # Use a supported runtime
  timeout                           = 5
  role_name                         = "lambda-role-${var.domain_name}-pre-token-generation-${local.region}"
  cloudwatch_logs_retention_in_days = 7

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

  # No Cognito trigger defined here
  allowed_triggers = {}

  tags = var.tags
}

# --- Separate Lambda Permission for Cognito to Invoke Pre Token Generation Lambda ---
resource "aws_lambda_permission" "allow_cognito_pre_token_generation" {
  statement_id  = "AllowCognitoInvokePreTokenGeneration"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_trigger_pre_token_generation.lambda_function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}

# --- Optional: Separate IAM Policy if Pre Token Lambda NEEDS to call Cognito APIs ---
# Most Pre Token Generation lambdas modify the event claims and don't need to call back to Cognito APIs.
# Add this ONLY if your lambda code *requires* calling actions like GetUser, AdminGetUser, etc.
/*
resource "aws_iam_role_policy" "lambda_pre_token_cognito_policy" {
  name = "${module.lambda_trigger_pre_token_generation.lambda_role_name}-cognito-perms"
  role = module.lambda_trigger_pre_token_generation.lambda_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Action    = [
            # Add specific Cognito actions needed by this lambda, e.g.:
            # "cognito-idp:GetUser",
            # "cognito-idp:AdminGetUser"
        ]
        Resource  = [aws_cognito_user_pool.main.arn]
      },
    ]
  })
}
*/
