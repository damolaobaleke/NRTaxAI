variable "project_name" { type = string }
variable "environment" { type = string }
variable "buckets" { type = map(any) }

# S3 Buckets
resource "aws_s3_bucket" "buckets" {
  for_each = var.buckets
  
  bucket = each.value.name
  
  tags = {
    Name = each.value.name
    Type = each.key
  }
}

# Versioning
resource "aws_s3_bucket_versioning" "buckets" {
  for_each = var.buckets
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  versioning_configuration {
    status = each.value.versioning ? "Enabled" : "Disabled"
  }
}

# Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "buckets" {
  for_each = { for k, v in var.buckets : k => v if v.encryption }
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# Block Public Access
resource "aws_s3_bucket_public_access_block" "buckets" {
  for_each = var.buckets
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}

# Lifecycle Rules
resource "aws_s3_bucket_lifecycle_configuration" "buckets" {
  for_each = { for k, v in var.buckets : k => v if length(v.lifecycle_rules) > 0 }
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  dynamic "rule" {
    for_each = each.value.lifecycle_rules
    
    content {
      id = rule.value.id
      status = rule.value.enabled ? "Enabled" : "Disabled"
      
      dynamic "transition" {
        for_each = lookup(rule.value, "transition_days", null) != null ? [1] : []
        
        content {
          days = rule.value.transition_days
          storage_class = rule.value.storage_class
        }
      }
      
      dynamic "expiration" {
        for_each = lookup(rule.value, "expiration_days", null) != null ? [1] : []
        
        content {
          days = rule.value.expiration_days
        }
      }
    }
  }
}

# CORS Configuration for uploads bucket
resource "aws_s3_bucket_cors_configuration" "uploads" {
  bucket = aws_s3_bucket.buckets["uploads"].id
  
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST"]
    allowed_origins = ["http://localhost:3000", "https://*.nrtaxai.com"]
    expose_headers = ["ETag"]
    max_age_seconds = 3000
  }
}

output "bucket_names" {
  value = { for k, v in aws_s3_bucket.buckets : k => v.bucket }
}

output "bucket_arns" {
  value = { for k, v in aws_s3_bucket.buckets : k => v.arn }
}
