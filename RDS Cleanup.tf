#Lambda to stopped running instances
data "archive_file" "sandbox_rds_stop_zip" {
  type        = "zip"
  source_file = "${path.module}/source/rds_stop/rds-stop-lambda-function.py"
  output_path = "${path.module}/output/rds-stop-lambda-function.zip"
}

resource "aws_lambda_function" "rds_stop" {
  filename         = "${path.module}/output/rds-stop-lambda-function.zip"
  function_name    = "${var.function_prefix}rds_stop"
  role             = "${aws_iam_role.iam_role_for_rds_cleanup.arn}"
  handler          = "rds-stop-lambda-function.lambda_handler"
  source_code_hash = "${data.archive_file.sandbox_rds_stop_zip.output_base64sha256}"
  runtime          = "python3.7"
  memory_size      = "512"
  timeout          = "30"
}

resource "aws_lambda_permission" "allow_cloudwatch_rds_stop" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.rds_stop.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.rds_stop_cloudwatch_rule.arn}"
}

resource "aws_cloudwatch_event_rule" "rds_stop_cloudwatch_rule" {
  name                = "rds_stop_lambda_trigger"
  schedule_expression = "${var.ec2_stop_instance_cron}"
}

resource "aws_cloudwatch_event_target" "rds_stop_lambda" {
  rule      = "${aws_cloudwatch_event_rule.rds_stop_cloudwatch_rule.name}"
  target_id = "rds_stop_lambda_target"
  arn       = "${aws_lambda_function.rds_stop.arn}"
}

#Lambda to terminate stopped instances.
data "archive_file" "sandbox_rds-terminate-lambda-function" {
  type        = "zip"
  source_file = "${path.module}/source/rds_terminate/rds-terminate-lambda-function.py"
  output_path = "${path.module}/output/rds-terminate-lambda-function.zip"
}

resource "aws_lambda_function" "rds-terminate-lambda-function" {
  filename         = "${path.module}/output/rds-terminate-lambda-function.zip"
  function_name    = "${var.function_prefix}rds-terminate-lambda-function"
  role             = "${aws_iam_role.iam_role_for_rds_cleanup.arn}"
  handler          = "rds-terminate-lambda-function.lambda_handler"
  source_code_hash = "${data.archive_file.sandbox_rds-terminate-lambda-function.output_base64sha256}"
  runtime          = "python3.7"
  memory_size      = "512"
  timeout          = "30"
}

resource "aws_lambda_permission" "allow_cloudwatch_rds-terminate-lambda-function" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.rds-terminate-lambda-function.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.rds-terminate-lambda-function_cloudwatch_rule.arn}"
}

resource "aws_cloudwatch_event_rule" "rds-terminate-lambda-function_cloudwatch_rule" {
  name                = "rds-terminate-lambda-function_lambda_trigger"
  schedule_expression = "${var.ec2_terminate_instance_cron}"
}

resource "aws_cloudwatch_event_target" "rds-terminate-lambda-function_lambda" {
  rule      = "${aws_cloudwatch_event_rule.rds-terminate-lambda-function_cloudwatch_rule.name}"
  target_id = "rds-terminate-lambda-function_lambda_target"
  arn       = "${aws_lambda_function.rds-terminate-lambda-function.arn}"
}
