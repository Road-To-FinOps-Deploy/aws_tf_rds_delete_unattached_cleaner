
terraform {
  required_version = ">= 0.12"
}

resource "aws_ses_email_identity" "sns_email" {
  email = var.sender_email
}
