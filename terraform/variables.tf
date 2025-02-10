# variables.tf
variable "aws_region" {
  default = "us-east-1"
}

variable "project_name" {
  default = "etl-project"
}

variable "environment" {
  default = "dev"
}
