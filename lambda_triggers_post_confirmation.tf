module "lambda_trigger_post_confirmation" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.20.1" # Use the desired version

  function_name                     = "${local.sanitized_domain_name}-cognito-post-confirmation"
  description                       = "Lambda function to set user_id after confirmation and store user data"
  handler                           = "index.lambda_handler"
  runtime                           = "python3.12" # Use a supported runtime
  timeout                           = 30
  role_name                         = "lambda-role-${local.sanitized_domain_name}-post-confirmation-${local.region}"
  cloudwatch_logs_retention_in_days = 7

  source_path = [
    {
      path             = "${path.module}/src/post_confirmation_lambda"
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

  # No Cognito trigger defined here
  allowed_triggers = {}

  tags = var.tags
}

# --- Separate IAM Policy for Lambda to Access Cognito ---
resource "aws_iam_role_policy" "lambda_post_confirmation_cognito_policy" {
  name = "${module.lambda_trigger_post_confirmation.lambda_role_name}-cognito-perms"
  role = module.lambda_trigger_post_confirmation.lambda_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["cognito-idp:AdminUpdateUserAttributes"]
        Resource = [aws_cognito_user_pool.main.arn]
      },
    ]
  })
}

# --- Separate Lambda Permission for Cognito to Invoke Lambda ---
resource "aws_lambda_permission" "allow_cognito_post_confirmation" {
  statement_id  = "AllowCognitoInvokePostConfirmation"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_trigger_post_confirmation.lambda_function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}
