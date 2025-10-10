variable "project_name" { type = string }
variable "environment" { type = string }
variable "functions" { type = map(any) }

# IAM Role for Lambda
resource "aws_iam_role" "lambda" {
  for_each = var.functions
  
  name = "${each.value.name}-role"
  
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

# Lambda Functions
resource "aws_lambda_function" "functions" {
  for_each = var.functions
  
  function_name = each.value.name
  handler = each.value.handler
  runtime = each.value.runtime
  timeout = each.value.timeout
  memory_size = each.value.memory_size
  
  filename = "${path.module}/../../../backend/lambda/${each.key}.zip"
  source_code_hash = filebase64sha256("${path.module}/../../../backend/lambda/${each.key}.zip")
  
  role = aws_iam_role.lambda[each.key].arn
  
  environment {
    variables = each.value.environment_variables
  }
  
  tags = {
    Name = each.value.name
  }
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "lambda" {
  for_each = var.functions
  
  name = "/aws/lambda/${each.value.name}"
  retention_in_days = 30
}

# IAM Policy for Lambda
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  for_each = var.functions
  
  role = aws_iam_role.lambda[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

output "function_arns" {
  value = { for k, v in aws_lambda_function.functions : k => v.arn }
}

output "function_names" {
  value = { for k, v in aws_lambda_function.functions : k => v.function_name }
}
