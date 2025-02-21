variable "rds_terminate_instance_cron" {
  default = "cron(0 23 ? * TUE *)"
}

variable "rds_stop_instance_cron" {
  default = "cron(0 23 ? * FRI *)"
}

variable "rds_find_connections_instance_cron" {
  default = "cron(0 23 ? * FRI *)"
}

variable "function_prefix" {
  default = ""
}

variable "region" {
  default = "eu-west-1"
}

variable "reciver_email" {
  default = "example@hotmail.com"
}

variable "sender_email" {
}