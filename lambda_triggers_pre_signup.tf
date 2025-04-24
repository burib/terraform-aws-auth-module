module "lambda_trigger_pre_signup" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.20.1" # Use the desired version

  function_name                     = "${local.sanitized_domain_name}-cognito-pre-signup"
  description                       = "Lambda function to add custom:user_id to cognito user attributes"
  handler                           = "index.lambda_handler"
  runtime                           = "python3.13" # Use a supported runtime
  timeout                           = 5
  role_name                         = "lambda-role-${local.sanitized_domain_name}-pre-signup-${local.region}"
  cloudwatch_logs_retention_in_days = 7

  source_path = [
    {
      path             = "${path.module}/src/pre_sign_up_lambda"
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

# --- Separate Lambda Permission for Cognito to Invoke Pre Sign Up Lambda ---
resource "aws_lambda_permission" "allow_cognito_pre_signup_generation" {
  statement_id  = "Allow${local.camel_case_domain_name}CognitoInvokePreSignUp${local.region}"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_trigger_pre_signup.lambda_function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}
