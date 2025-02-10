# main.tf
# S3 Bucket
resource "aws_s3_bucket" "data_bucket" {
  bucket = "${var.project_name}-${var.environment}-data"
}

# RDS Instance
resource "aws_db_instance" "postgres" {
  identifier           = "${var.project_name}-${var.environment}"
  engine              = "postgres"
  engine_version      = "13.7"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  skip_final_snapshot = true

  db_name  = "etldb"
  username = "etluser"
  password = "your-secure-password"  # Use AWS Secrets Manager in production
}

# ECR Repository
resource "aws_ecr_repository" "app" {
  name = "${var.project_name}-${var.environment}"
}

# Glue Database
resource "aws_glue_catalog_database" "etl_db" {
  name = "${var.project_name}_${var.environment}_db"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-${var.environment}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-${var.environment}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "glue:CreateTable",
          "glue:UpdateTable"
        ]
        Resource = [
          "${aws_s3_bucket.data_bucket.arn}/*",
          aws_glue_catalog_database.etl_db.arn
        ]
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "etl_function" {
  function_name = "${var.project_name}-${var.environment}-etl"
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:latest"

  environment {
    variables = {
      SOURCE_BUCKET  = aws_s3_bucket.data_bucket.id
      DATABASE_NAME  = aws_glue_catalog_database.etl_db.name
      DB_HOST        = aws_db_instance.postgres.endpoint
      DB_NAME        = aws_db_instance.postgres.db_name
      DB_USER        = aws_db_instance.postgres.username
      DB_PASSWORD    = aws_db_instance.postgres.password
    }
  }
}