variable "project_name" { type = string }
variable "environment" { type = string }
variable "instance_class" { type = string }
variable "allocated_storage" { type = number }
variable "database_name" { type = string }
variable "master_username" { type = string }
variable "vpc_id" { type = string }
variable "database_subnet_ids" { type = list(string) }
variable "backup_retention_period" { type = number }
variable "backup_window" { type = string }
variable "maintenance_window" { type = string }
variable "multi_az" { type = bool }
variable "storage_encrypted" { type = bool }
variable "allowed_security_groups" { type = list(string) }

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name = "${var.project_name}-db-subnet-group"
  subnet_ids = var.database_subnet_ids
  
  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# Security Group
resource "aws_security_group" "rds" {
  name = "${var.project_name}-rds-sg"
  vpc_id = var.vpc_id
  
  ingress {
    from_port = 5432
    to_port = 5432
    protocol = "tcp"
    security_groups = var.allowed_security_groups
  }
  
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-postgres"
  
  engine = "postgres"
  engine_version = "15.4"
  instance_class = var.instance_class
  
  allocated_storage = var.allocated_storage
  storage_type = "gp3"
  storage_encrypted = var.storage_encrypted
  
  db_name = var.database_name
  username = var.master_username
  password = random_password.db_password.result
  
  db_subnet_group_name = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  multi_az = var.multi_az
  
  backup_retention_period = var.backup_retention_period
  backup_window = var.backup_window
  maintenance_window = var.maintenance_window
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "${var.project_name}-final-snapshot-${formatdate("YYYYMMDD-hhmmss", timestamp())}"
  
  tags = {
    Name = "${var.project_name}-postgres"
  }
}

# Random password for database
resource "random_password" "db_password" {
  length = 32
  special = true
}

# Store password in Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.project_name}/db-password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id = aws_secretsmanager_secret.db_password.id
  secret_string = jsonencode({
    username = var.master_username
    password = random_password.db_password.result
    engine = "postgres"
    host = aws_db_instance.main.endpoint
    port = 5432
    dbname = var.database_name
  })
}

output "db_endpoint" {
  value = aws_db_instance.main.endpoint
}

output "db_username" {
  value = var.master_username
}

output "db_password" {
  value = random_password.db_password.result
  sensitive = true
}

output "db_security_group_id" {
  value = aws_security_group.rds.id
}
