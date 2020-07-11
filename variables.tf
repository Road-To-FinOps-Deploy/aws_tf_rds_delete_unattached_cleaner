variable "rds_terminate_instance_cron" {
  default = "cron(0 23 ? * TUE *)"
}

variable "rds_stop_instance_cron" {
  default = "cron(0 23 ? * FRI *)"
}

variable "function_prefix" {
  default = ""
}

