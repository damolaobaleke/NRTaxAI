variable "project_name" { type = string }
variable "environment" { type = string }
variable "queues" { type = map(any) }

# SQS Queues
resource "aws_sqs_queue" "queues" {
  for_each = var.queues
  
  name = each.value.name
  
  visibility_timeout_seconds = each.value.visibility_timeout_seconds
  message_retention_seconds = each.value.message_retention_seconds
  
  sqs_managed_sse_enabled = true
  
  tags = {
    Name = each.value.name
    Type = each.key
  }
}

# Dead Letter Queues
resource "aws_sqs_queue" "dlq" {
  for_each = { for k, v in var.queues : k => v if v.dead_letter_queue }
  
  name = "${each.value.name}-dlq"
  
  message_retention_seconds = 1209600  # 14 days
  
  sqs_managed_sse_enabled = true
}

# Redrive Policy
resource "aws_sqs_queue_redrive_policy" "main" {
  for_each = { for k, v in var.queues : k => v if v.dead_letter_queue }
  
  queue_url = aws_sqs_queue.queues[each.key].id
  
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount = 3
  })
}

output "queue_urls" {
  value = { for k, v in aws_sqs_queue.queues : k => v.url }
}

output "queue_arns" {
  value = { for k, v in aws_sqs_queue.queues : k => v.arn
}
