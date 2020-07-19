#Lambda to stopped running instances
data "archive_file" "rds_find_connections_zip" {
  type        = "zip"
  source_file = "${path.module}/source/rds_find_connections/lambda.py"
  output_path = "${path.module}/output/rds_find_connections.zip"
}

resource "aws_lambda_function" "rds_find_connections" {
  filename         = "${path.module}/output/rds_find_connections.zip"
  function_name    = "${var.function_prefix}rds_find_connections"
  role             = aws_iam_role.iam_role_for_rds_cleanup.arn
  handler          = "lambda.lambda_handler"
  source_code_hash = data.archive_file.rds_find_connections_zip.output_base64sha256
  runtime          = "python3.7"
  memory_size      = "512"
  timeout          = "30"
}

resource "aws_lambda_permission" "allow_cloudwatch_rds_find_connections" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rds_find_connections.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.rds_find_connections_cloudwatch_rule.arn
}

resource "aws_cloudwatch_event_rule" "rds_find_connections_cloudwatch_rule" {
  name                = "rds_find_connections_lambda_trigger"
  schedule_expression = var.rds_find_connections_instance_cron
}

resource "aws_cloudwatch_event_target" "rds_find_connections_lambda" {
  rule      = aws_cloudwatch_event_rule.rds_find_connections_cloudwatch_rule.name
  target_id = "rds_find_connections_lambda_target"
  arn       = aws_lambda_function.rds_find_connections.arn
}
