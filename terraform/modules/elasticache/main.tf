variable "project_name" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "node_type" { type = string }
variable "num_cache_nodes" { type = number }
variable "allowed_security_groups" { type = list(string) }

# Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name = "${var.project_name}-redis-subnet-group"
  subnet_ids = var.private_subnet_ids
}

# Security Group
resource "aws_security_group" "redis" {
  name = "${var.project_name}-redis-sg"
  vpc_id = var.vpc_id
  
  ingress {
    from_port = 6379
    to_port = 6379
    protocol = "tcp"
    security_groups = var.allowed_security_groups
  }
  
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ElastiCache Redis
resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${var.project_name}-redis"
  description = "Redis cache for ${var.project_name}"
  
  engine = "redis"
  engine_version = "7.0"
  node_type = var.node_type
  num_cache_clusters = var.num_cache_nodes
  
  port = 6379
  
  subnet_group_name = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  automatic_failover_enabled = true
  multi_az_enabled = true
  
  snapshot_retention_limit = 7
  snapshot_window = "03:00-05:00"
  
  log_delivery_configuration {
    destination = "${var.project_name}-redis-logs"
    destination_type = "cloudwatch-logs"
    log_format = "json"
    log_type = "slow-log"
  }
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "redis_port" {
  value = 6379
}
