resource "aws_cloudwatch_metric_alarm" "auth_errors" {
  count = var.alert_email != "" ? 1 : 0

  alarm_name          = "${var.domain_name}-auth-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Cognito"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Authentication errors exceeded threshold"
  alarm_actions       = [aws_sns_topic.auth_alerts[0].arn]

  dimensions = {
    UserPool = aws_cognito_user_pool.main.id
  }

  tags = var.tags
}

# SNS Topic for Alerts
resource "aws_sns_topic" "auth_alerts" {
  count = var.alert_email != "" ? 1 : 0

  name = "${var.domain_name}-auth-alerts"
  tags = var.tags
}

resource "aws_sns_topic_subscription" "auth_alerts_email" {
  count = var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.auth_alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}