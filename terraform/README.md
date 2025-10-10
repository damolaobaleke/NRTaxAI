# NRTaxAI Infrastructure - Terraform

## Overview

This directory contains Terraform configurations for deploying the NRTaxAI infrastructure on AWS.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────────────┐    ┌──────────────┐    │
│  │   WAF    │───▶│  Load Balancer   │───▶│  ECS Fargate │    │
│  └──────────┘    └──────────────────┘    └──────────────┘    │
│                           │                       │            │
│                           ▼                       ▼            │
│                   ┌──────────────┐       ┌──────────────┐    │
│                   │  CloudWatch  │       │  RDS Postgres│    │
│                   │  Logs/Metrics│       │  (Multi-AZ)  │    │
│                   └──────────────┘       └──────────────┘    │
│                                                 │              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │  S3 Buckets  │    │  ElastiCache │    │  Lambda      │    │
│  │  (3 buckets) │    │  Redis       │    │  Functions   │    │
│  └──────────────┘    └──────────────┘    └──────────────┘    │
│         │                                        │             │
│         ▼                                        ▼             │
│  ┌──────────────┐                      ┌──────────────┐       │
│  │  KMS         │                      │  Textract    │       │
│  │  Encryption  │                      │  Service     │       │
│  └──────────────┘                      └──────────────┘       │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Resources Deployed

### Networking
- **VPC** with public, private, and database subnets across 3 AZs
- **NAT Gateways** for private subnet internet access
- **Security Groups** with least privilege access

### Compute
- **ECS Fargate Cluster** for backend API
- **Application Load Balancer** with WAF protection
- **Auto Scaling** based on CPU utilization (2-10 tasks)

### Database
- **RDS PostgreSQL 15** (Multi-AZ)
- Automated backups (30 days retention)
- Encryption at rest with KMS
- Point-in-time recovery enabled

### Caching
- **ElastiCache Redis** (Multi-AZ replication)
- Encryption in transit and at rest
- Automatic failover

### Storage
- **S3 Buckets**:
  - `nrtaxai-uploads` - User document uploads
  - `nrtaxai-pdfs` - Generated tax forms
  - `nrtaxai-extracts` - Textract extraction results
  - `nrtaxai-backups` - Backup storage
- Versioning enabled
- Lifecycle policies for Glacier archival
- Cross-region replication for DR

### Serverless
- **Lambda Functions**:
  - `av-scanner` - Antivirus scanning
  - `textract-processor` - Document OCR processing
- **SQS Queues**:
  - `document-processing` - Async document processing
  - `email-notifications` - Email delivery

### Security
- **KMS Key** for data encryption
- **WAF** with managed rule sets and custom rules
- **IAM Roles** with least privilege
- **Secrets Manager** for sensitive credentials

### Monitoring
- **CloudWatch Logs** for all services
- **CloudWatch Metrics** for performance monitoring
- **CloudWatch Alarms** for critical alerts

## Prerequisites

1. AWS Account with appropriate permissions
2. Terraform >= 1.0 installed
3. AWS CLI configured
4. S3 bucket for Terraform state (create first)
5. DynamoDB table for state locking (create first)

## Initial Setup

### 1. Create Terraform State Backend

```bash
# Create S3 bucket for state
aws s3 mb s3://nrtaxai-terraform-state --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket nrtaxai-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket nrtaxai-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Create DynamoDB table for locking
aws dynamodb create-table \
  --table-name nrtaxai-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 2. Initialize Terraform

```bash
cd terraform
terraform init
```

### 3. Create terraform.tfvars

```hcl
aws_region = "us-east-1"
environment = "production"
project_name = "nrtaxai"
```

## Deployment

### Plan Changes

```bash
terraform plan
```

### Apply Infrastructure

```bash
terraform apply
```

### Destroy Infrastructure (CAUTION!)

```bash
terraform destroy
```

## Environment-Specific Deployments

### Development

```bash
terraform workspace new development
terraform workspace select development
terraform apply -var-file="environments/development.tfvars"
```

### Staging

```bash
terraform workspace new staging
terraform workspace select staging
terraform apply -var-file="environments/staging.tfvars"
```

### Production

```bash
terraform workspace new production
terraform workspace select production
terraform apply -var-file="environments/production.tfvars"
```

## Post-Deployment

### 1. Update Database Schema

```bash
# Get RDS endpoint from Terraform output
terraform output rds_endpoint

# Run migrations
cd ../backend
python init_db.py
```

### 2. Deploy Application

```bash
# Build and push Docker image
docker build -t nrtaxai-backend:latest ./backend
docker tag nrtaxai-backend:latest <ECR_URL>/nrtaxai-backend:latest
docker push <ECR_URL>/nrtaxai-backend:latest

# Update ECS service
aws ecs update-service \
  --cluster nrtaxai-cluster \
  --service nrtaxai-service \
  --force-new-deployment
```

### 3. Configure DNS

```bash
# Get ALB DNS name
terraform output alb_dns_name

# Create Route53 record pointing to ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.nrtaxai.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "<ALB_DNS_NAME>"}]
      }
    }]
  }'
```

## Monitoring

### CloudWatch Dashboards

```bash
# Create custom dashboard
aws cloudwatch put-dashboard \
  --dashboard-name NRTaxAI-Production \
  --dashboard-body file://cloudwatch-dashboard.json
```

### Alarms

Key alarms configured:
- ECS CPU > 70%
- ECS Memory > 80%
- RDS CPU > 80%
- RDS Free Storage < 10GB
- WAF Blocked Requests > 100/5min
- Lambda Errors > 10/5min

## Backup & Recovery

### Database Backups

- **Automated**: Daily at 3:00 AM UTC (30 days retention)
- **Manual Snapshots**: Created before deployments
- **Point-in-Time Recovery**: Up to 7 days

### S3 Backups

- **Versioning**: Enabled on all buckets
- **Cross-Region Replication**: To us-west-2
- **Lifecycle Policies**: Archive to Glacier after 90 days

### Disaster Recovery

**RTO**: 4 hours  
**RPO**: 1 hour

Recovery steps:
1. Switch to DR region (us-west-2)
2. Restore RDS from latest snapshot
3. Update DNS to DR ALB
4. Verify application health

## Cost Optimization

### Estimated Monthly Costs (Production)

| Service | Configuration | Est. Cost |
|---------|--------------|-----------|
| ECS Fargate | 2 tasks (1 vCPU, 2GB) | $60 |
| RDS PostgreSQL | db.t3.large Multi-AZ | $350 |
| ElastiCache Redis | 2 nodes cache.t3.medium | $120 |
| S3 Storage | 100GB + requests | $25 |
| NAT Gateway | 3 gateways | $100 |
| ALB | + data transfer | $25 |
| Lambda | 1M invocations | $20 |
| CloudWatch | Logs + metrics | $30 |
| **Total** | | **~$730/month** |

### Cost Reduction Tips

1. Use Reserved Instances for RDS (save 40%)
2. Enable S3 Intelligent-Tiering
3. Use Spot instances for development
4. Implement CloudWatch Logs retention policies
5. Review and delete unused snapshots

## Security Checklist

- [x] VPC with private subnets
- [x] Security groups with minimal ports
- [x] RDS encryption at rest (KMS)
- [x] S3 bucket encryption
- [x] WAF with managed rule sets
- [x] IAM roles with least privilege
- [x] Secrets Manager for credentials
- [x] CloudWatch logging enabled
- [x] MFA delete on S3 buckets
- [x] Automated backups configured

## Troubleshooting

### Common Issues

**Issue**: Terraform state locked  
**Solution**: 
```bash
terraform force-unlock <LOCK_ID>
```

**Issue**: ECS tasks failing health checks  
**Solution**: Check CloudWatch logs and security group rules

**Issue**: RDS connection timeout  
**Solution**: Verify security group allows ECS SG on port 5432

## Maintenance

### Regular Tasks

- **Weekly**: Review CloudWatch alarms
- **Monthly**: Review and cleanup old snapshots
- **Quarterly**: Review IAM policies and access
- **Annually**: Update Terraform providers

## Support

For infrastructure issues, check:
1. CloudWatch Logs
2. AWS Health Dashboard
3. Terraform state file
4. AWS Support Center
