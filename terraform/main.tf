terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "nrtaxai-terraform-state"
    key    = "terraform.tfstate"
    region = "us-east-1"
    encrypt = true
    dynamodb_table = "nrtaxai-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "NRTaxAI"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "nrtaxai"
}

# VPC Configuration
module "vpc" {
  source = "./modules/vpc"
  
  project_name = var.project_name
  environment  = var.environment
  
  vpc_cidr = "10.0.0.0/16"
  
  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
  
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
  database_subnet_cidrs = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]
}

# RDS PostgreSQL
module "rds" {
  source = "./modules/rds"
  
  project_name = var.project_name
  environment  = var.environment
  
  instance_class = "db.t3.large"
  allocated_storage = 100
  
  database_name = "nrtaxai"
  master_username = "nrtaxai_admin"
  
  vpc_id = module.vpc.vpc_id
  database_subnet_ids = module.vpc.database_subnet_ids
  
  backup_retention_period = 30
  backup_window = "03:00-04:00"
  maintenance_window = "sun:04:00-sun:05:00"
  
  multi_az = true
  storage_encrypted = true
  
  allowed_security_groups = [module.ecs.ecs_security_group_id]
}

# S3 Buckets
module "s3" {
  source = "./modules/s3"
  
  project_name = var.project_name
  environment  = var.environment
  
  buckets = {
    uploads = {
      name = "${var.project_name}-uploads"
      versioning = true
      encryption = true
      lifecycle_rules = [
        {
          id = "archive-old-uploads"
          enabled = true
          transition_days = 90
          storage_class = "GLACIER"
        }
      ]
    }
    
    pdfs = {
      name = "${var.project_name}-pdfs"
      versioning = true
      encryption = true
      lifecycle_rules = [
        {
          id = "archive-old-pdfs"
          enabled = true
          transition_days = 180
          storage_class = "GLACIER"
        }
      ]
    }
    
    extracts = {
      name = "${var.project_name}-extracts"
      versioning = true
      encryption = true
      lifecycle_rules = [
        {
          id = "expire-old-extracts"
          enabled = true
          expiration_days = 365
        }
      ]
    }
    
    backups = {
      name = "${var.project_name}-backups"
      versioning = true
      encryption = true
      lifecycle_rules = []
    }
  }
}

# ECS Cluster for Backend API
module "ecs" {
  source = "./modules/ecs"
  
  project_name = var.project_name
  environment  = var.environment
  service_name = "backend"
  
  vpc_id = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids = module.vpc.public_subnet_ids
  
  container_image = "${var.project_name}-backend:latest"
  container_port = 8000
  
  cpu = 1024
  memory = 2048
  desired_count = 2
  
  environment_variables = {
    ENVIRONMENT = var.environment
    DATABASE_URL = "postgresql://${module.rds.db_username}:${module.rds.db_password}@${module.rds.db_endpoint}/nrtaxai"
    REDIS_URL = "redis://${module.elasticache.redis_endpoint}:6379"
    S3_BUCKET_UPLOADS = module.s3.bucket_names["uploads"]
    S3_BUCKET_PDFS = module.s3.bucket_names["pdfs"]
    S3_BUCKET_EXTRACTS = module.s3.bucket_names["extracts"]
  }
  
  secrets = {
    SECRET_KEY = "${var.project_name}/SECRET_KEY"
    OPENAI_API_KEY = "${var.project_name}/OPENAI_API_KEY"
    AWS_ACCESS_KEY_ID = "${var.project_name}/AWS_ACCESS_KEY_ID"
    AWS_SECRET_ACCESS_KEY = "${var.project_name}/AWS_SECRET_ACCESS_KEY"
  }
  
  health_check_path = "/api/v1/health"
}

# S3 Bucket for Frontend
resource "aws_s3_bucket" "frontend" {
  bucket = "${var.project_name}-frontend"
  
  tags = {
    Name = "${var.project_name}-frontend"
    Type = "frontend"
  }
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  
  index_document {
    suffix = "index.html"
  }
  
  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  
  block_public_acls = false
  block_public_policy = false
  ignore_public_acls = false
  restrict_public_buckets = false
}

# CloudFront Distribution for Frontend
resource "aws_cloudfront_distribution" "frontend" {
  enabled = true
  default_root_object = "index.html"
  
  origin {
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id = "S3-${aws_s3_bucket.frontend.id}"
    
    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.frontend.cloudfront_access_identity_path
    }
  }
  
  default_cache_behavior {
    allowed_methods = ["GET", "HEAD", "OPTIONS"]
    cached_methods = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.frontend.id}"
    
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl = 0
    default_ttl = 3600
    max_ttl = 86400
    compress = true
  }
  
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  viewer_certificate {
    cloudfront_default_certificate = true
  }
  
  custom_error_response {
    error_code = 404
    response_code = 200
    response_page_path = "/index.html"
  }
  
  tags = {
    Name = "${var.project_name}-cloudfront"
  }
}

resource "aws_cloudfront_origin_access_identity" "frontend" {
  comment = "OAI for ${var.project_name} frontend"
}

# ElastiCache Redis
module "elasticache" {
  source = "./modules/elasticache"
  
  project_name = var.project_name
  environment  = var.environment
  
  vpc_id = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  
  node_type = "cache.t3.medium"
  num_cache_nodes = 2
  
  allowed_security_groups = [module.ecs.ecs_security_group_id]
}

# SQS Queues
module "sqs" {
  source = "./modules/sqs"
  
  project_name = var.project_name
  environment  = var.environment
  
  queues = {
    document_processing = {
      name = "${var.project_name}-document-processing"
      visibility_timeout_seconds = 300
      message_retention_seconds = 1209600
      dead_letter_queue = true
    }
    
    email_notifications = {
      name = "${var.project_name}-email-notifications"
      visibility_timeout_seconds = 60
      message_retention_seconds = 345600
      dead_letter_queue = true
    }
  }
}

# Lambda Functions
module "lambda" {
  source = "./modules/lambda"
  
  project_name = var.project_name
  environment  = var.environment
  
  functions = {
    av_scanner = {
      name = "${var.project_name}-av-scanner"
      handler = "av_scanner.lambda_handler"
      runtime = "python3.9"
      timeout = 300
      memory_size = 1024
      
      environment_variables = {
        S3_BUCKET_UPLOADS = module.s3.bucket_names["uploads"]
      }
    }
    
    textract_processor = {
      name = "${var.project_name}-textract-processor"
      handler = "textract_processor.lambda_handler"
      runtime = "python3.9"
      timeout = 600
      memory_size = 2048
      
      environment_variables = {
        S3_BUCKET_UPLOADS = module.s3.bucket_names["uploads"]
        S3_BUCKET_EXTRACTS = module.s3.bucket_names["extracts"]
        SQS_QUEUE_URL = module.sqs.queue_urls["document_processing"]
      }
    }
  }
}

# KMS Key for Encryption
resource "aws_kms_key" "main" {
  description = "KMS key for NRTaxAI PII encryption"
  
  enable_key_rotation = true
  
  tags = {
    Name = "${var.project_name}-kms-key"
  }
}

resource "aws_kms_alias" "main" {
  name = "alias/${var.project_name}-main"
  target_key_id = aws_kms_key.main.key_id
}

# WAF Web ACL
module "waf" {
  source = "./modules/waf"
  
  project_name = var.project_name
  environment  = var.environment
  
  alb_arn = module.ecs.alb_arn
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name = "/aws/ecs/${var.project_name}-${var.environment}"
  retention_in_days = 30
  
  tags = {
    Name = "${var.project_name}-ecs-logs"
  }
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name = "/aws/lambda/${var.project_name}"
  retention_in_days = 30
}

# Outputs
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "rds_endpoint" {
  value = module.rds.db_endpoint
  sensitive = true
}

output "redis_endpoint" {
  value = module.elasticache.redis_endpoint
}

output "backend_alb_dns_name" {
  value = module.ecs.alb_dns_name
  description = "Backend API Load Balancer DNS"
}

output "frontend_cloudfront_url" {
  value = aws_cloudfront_distribution.frontend.domain_name
  description = "Frontend CloudFront URL"
}

output "frontend_s3_bucket" {
  value = aws_s3_bucket.frontend.id
  description = "Frontend S3 Bucket"
}

output "s3_bucket_names" {
  value = module.s3.bucket_names
}

output "kms_key_id" {
  value = aws_kms_key.main.id
}
