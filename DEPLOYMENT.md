# NRTaxAI Deployment Guide

## Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/your-org/nrtaxai.git
cd nrtaxai

# Copy environment variables
cp backend/env.example backend/.env
# Edit backend/.env with your credentials

# Start all services with Docker Compose
docker-compose up -d

# Initialize database
docker-compose exec backend python init_db.py

# Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Setup (Without Docker)

#### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env.example .env
# Edit .env with your credentials

# Initialize database
python init_db.py

# Run development server
uvicorn main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > .env

# Run development server
npm start
```

## Production Deployment

### Prerequisites

1. AWS Account with appropriate permissions
2. Domain name configured
3. SSL certificate in AWS Certificate Manager
4. Terraform installed
5. Docker installed

### Step 1: Infrastructure Deployment

```bash
cd terraform

# Initialize Terraform
terraform init

# Create production workspace
terraform workspace new production
terraform workspace select production

# Plan infrastructure
terraform plan -var-file="environments/production.tfvars"

# Apply infrastructure
terraform apply -var-file="environments/production.tfvars"

# Note the outputs
terraform output
```

### Step 2: Database Setup

```bash
# Get RDS endpoint
export DB_ENDPOINT=$(terraform output -raw rds_endpoint)

# Run migrations
cd ../backend
python init_db.py
```

### Step 3: Backend Deployment

```bash
# Build Docker image
docker build -t nrtaxai-backend:latest ./backend

# Tag for ECR
export ECR_REPOSITORY=$(terraform output -raw ecr_repository_url)
docker tag nrtaxai-backend:latest $ECR_REPOSITORY:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REPOSITORY
docker push $ECR_REPOSITORY:latest

# Update ECS service
aws ecs update-service \
  --cluster nrtaxai-cluster \
  --service nrtaxai-service \
  --force-new-deployment
```

### Step 4: Frontend Deployment

```bash
cd frontend

# Install dependencies
npm ci

# Build for production
REACT_APP_API_URL=https://api.nrtaxai.com/api/v1 npm run build

# Deploy to S3
aws s3 sync build/ s3://nrtaxai-frontend --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

### Step 5: Configure Secrets

```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name nrtaxai/SECRET_KEY \
  --secret-string "your-production-secret-key"

aws secretsmanager create-secret \
  --name nrtaxai/OPENAI_API_KEY \
  --secret-string "sk-your-openai-api-key"

aws secretsmanager create-secret \
  --name nrtaxai/AWS_ACCESS_KEY_ID \
  --secret-string "your-aws-access-key"

aws secretsmanager create-secret \
  --name nrtaxai/AWS_SECRET_ACCESS_KEY \
  --secret-string "your-aws-secret-key"
```

### Step 6: Verify Deployment

```bash
# Check health
curl https://api.nrtaxai.com/api/v1/health

# Check detailed health
curl https://api.nrtaxai.com/api/v1/health/detailed

# Access frontend
open https://nrtaxai.com
```

## CI/CD Pipeline

The project uses GitHub Actions for automated CI/CD.

### Workflow Triggers

- **Push to `main`**: Deploys to production
- **Push to `develop`**: Deploys to staging
- **Pull Requests**: Runs tests and security scans

### Required GitHub Secrets

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
DATABASE_URL
OPENAI_API_KEY
KMS_KEY_ID
CLOUDFRONT_DISTRIBUTION_ID
SLACK_WEBHOOK (optional)
REACT_APP_API_URL
```

## Monitoring

### CloudWatch Dashboards

Access dashboards at: https://console.aws.amazon.com/cloudwatch/

Key dashboards:
- NRTaxAI-Production-Overview
- NRTaxAI-ECS-Metrics
- NRTaxAI-RDS-Metrics
- NRTaxAI-Lambda-Metrics

### Alerts

Alerts are sent to:
- **Critical**: ops@nrtaxai.com + SMS
- **Warning**: dev@nrtaxai.com
- **Info**: Slack #alerts channel

### Logs

Access logs:
- ECS Logs: `/aws/ecs/nrtaxai-production`
- Lambda Logs: `/aws/lambda/nrtaxai-*`
- RDS Logs: PostgreSQL slow query logs

## Backup & Recovery

### Automated Backups

- **Database**: Daily at 3:00 AM UTC (30 days retention)
- **S3 Files**: Versioning enabled + cross-region replication
- **Configuration**: Terraform state in S3 with versioning

### Manual Backup

```bash
# Create database snapshot
aws rds create-db-snapshot \
  --db-instance-identifier nrtaxai-postgres \
  --db-snapshot-identifier manual-backup-$(date +%Y%m%d)

# Export configuration
terraform state pull > terraform-state-backup.json
```

### Disaster Recovery

**RTO**: 4 hours  
**RPO**: 1 hour

```bash
# 1. Restore database
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier nrtaxai-postgres-restored \
  --db-snapshot-identifier latest-snapshot

# 2. Update application configuration
# 3. Verify data integrity
# 4. Update DNS
```

## Security Checklist

Before going to production:

- [ ] Change all default passwords
- [ ] Configure AWS WAF rules
- [ ] Enable RDS encryption
- [ ] Enable S3 encryption
- [ ] Configure KMS key rotation
- [ ] Set up VPC flow logs
- [ ] Enable CloudTrail logging
- [ ] Configure security groups (least privilege)
- [ ] Set up SSL/TLS certificates
- [ ] Enable MFA for AWS root account
- [ ] Configure backup policies
- [ ] Set up incident response procedures
- [ ] Review IAM policies
- [ ] Enable GuardDuty
- [ ] Configure AWS Config rules

## Troubleshooting

### Common Issues

**Backend won't start**
```bash
# Check logs
docker-compose logs backend

# Verify database connection
docker-compose exec backend python -c "import asyncpg; print('OK')"
```

**Frontend can't reach backend**
```bash
# Check CORS configuration
# Verify REACT_APP_API_URL in .env
# Check network connectivity
```

**Database connection errors**
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres psql -U nrtaxai -d nrtaxai -c "SELECT 1;"
```

## Performance Optimization

### Database

- Enable connection pooling (PgBouncer)
- Configure indexes for frequently queried fields
- Use materialized views for complex queries
- Monitor slow query log

### API

- Enable Redis caching for frequently accessed data
- Use CDN (CloudFront) for static assets
- Implement response compression
- Use async/await for I/O operations

### Cost Optimization

- Use RDS Reserved Instances (save 40%)
- Enable S3 Intelligent-Tiering
- Use Spot instances for non-critical workloads
- Implement CloudWatch Logs retention policies
- Clean up old snapshots regularly

## Support

- Documentation: https://docs.nrtaxai.com
- Issues: https://github.com/your-org/nrtaxai/issues
- Email: support@nrtaxai.com
