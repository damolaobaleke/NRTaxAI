# NRTaxAI System Architecture

## Architecture Overview

```
                                  Internet
                                     │
                                     ▼
                            ┌─────────────────┐
                            │   Route 53 DNS  │
                            │   nrtaxai.com   │
                            └─────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
          ┌──────────────────┐            ┌──────────────────┐
          │  CloudFront CDN  │            │   AWS WAF        │
          │  Frontend Assets │            │   Protection     │
          └──────────────────┘            └──────────────────┘
                    │                                 │
                    ▼                                 ▼
          ┌──────────────────┐            ┌──────────────────┐
          │  S3 Bucket       │            │  Application     │
          │  Frontend Static │            │  Load Balancer   │
          │  React Build     │            │  Backend API     │
          └──────────────────┘            └──────────────────┘
                                                    │
                                                    ▼
                                          ┌───────────────────┐
                                          │  ECS Fargate      │
                                          │  Backend Service  │
                                          │  - FastAPI        │
                                          │  - Port 8000      │
                                          │  - 2-10 tasks     │
                                          │  - Auto-scaling   │
                                          └───────────────────┘
                                                    │
                                    ┌───────────────┴───────────────┐
                                    │                               │
                                    ▼                               ▼
                          ┌──────────────────┐          ┌──────────────────┐
                          │  ElastiCache     │          │  RDS PostgreSQL  │
                          │  Redis           │          │  Multi-AZ        │
                          │  - Session cache │          │  - Primary DB    │
                          │  - Query cache   │          │  - Standby DB    │
                          └──────────────────┘          └──────────────────┘
                                    │
                                    ▼
                          ┌────────────────────────────────────────┐
                          │  AWS Services                          │
                          │  ┌──────┐  ┌──────┐  ┌──────┐        │
                          │  │  S3  │  │Lambda│  │Txtract│        │
                          │  │ KMS  │  │ SQS  │  │CWatch │        │
                          │  └──────┘  └──────┘  └──────┘        │
                          └────────────────────────────────────────┘
```

## Deployment Architecture

### Frontend (S3 + CloudFront)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CloudFront Distribution (CDN)                                  │
│  ├─ Global edge locations                                      │
│  ├─ HTTPS/TLS 1.3                                              │
│  ├─ Gzip compression                                            │
│  ├─- Cache static assets (1 year)                              │
│  └─ Custom error pages (SPA routing)                           │
│                    ↓                                            │
│  S3 Bucket (nrtaxai-frontend)                                   │
│  ├─ React build files (HTML, JS, CSS)                          │
│  ├─ Versioning enabled                                          │
│  ├─ Server-side encryption                                      │
│  └─ CloudFront OAI (Origin Access Identity)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Backend (ECS Fargate)

```
┌─────────────────────────────────────────────────────────────────┐
│                Backend Service (ECS Fargate)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Backend Service (nrtaxai-backend-service)                 │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ • Docker Image: ECR/nrtaxai-backend:latest               │ │
│  │ • Tasks: 2-10 (auto-scaling)                              │ │
│  │ • CPU: 1 vCPU                                             │ │
│  │ • Memory: 2 GB                                            │ │
│  │ • Port: 8000 (FastAPI)                                    │ │
│  │ • Health Check: GET /api/v1/health                        │ │
│  │ • ALB: nrtaxai-backend-alb                                │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      VPC (10.0.0.0/16)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Public Subnets (3 AZs)                                  │   │
│  │ - 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24               │   │
│  │                                                         │   │
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │ │ Frontend ALB│  │ Backend ALB │  │ NAT Gateway │    │   │
│  │ └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Private Subnets (3 AZs)                                 │   │
│  │ - 10.0.11.0/24, 10.0.12.0/24, 10.0.13.0/24            │   │
│  │                                                         │   │
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │ │Frontend Task│  │Backend Task │  │  Redis      │    │   │
│  │ │Frontend Task│  │Backend Task │  │  (Multi-AZ) │    │   │
│  │ └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Database Subnets (3 AZs)                                │   │
│  │ - 10.0.21.0/24, 10.0.22.0/24, 10.0.23.0/24            │   │
│  │                                                         │   │
│  │ ┌─────────────────────────────────────────────┐        │   │
│  │ │ RDS PostgreSQL (Multi-AZ)                   │        │   │
│  │ │ - Primary: us-east-1a                       │        │   │
│  │ │ - Standby: us-east-1b                       │        │   │
│  │ └─────────────────────────────────────────────┘        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Benefits of S3 + CloudFront for Frontend

### ✅ Cost-Effective
- **S3 Storage**: ~$1-2/month for static files
- **CloudFront**: ~$3-5/month for CDN
- **Total**: ~$5-10/month vs $30/month for ECS task
- **Savings**: ~$20-25/month

### ✅ Performance
- Global CDN with edge locations worldwide
- Cached content served from nearest edge location
- Sub-100ms response times globally
- Automatic Gzip/Brotli compression

### ✅ Scalability
- Unlimited concurrent users
- No server capacity planning needed
- Automatic scaling globally
- No cold starts or warm-up time

### ✅ Reliability
- 99.99% SLA from CloudFront
- No server maintenance required
- Automatic failover across regions
- Built-in DDoS protection

### ✅ Simplicity
- No container orchestration for static files
- Simple `npm run build` → S3 sync
- Instant rollbacks (S3 versioning)
- Minimal operational overhead

## Deployment Flow

### CI/CD Pipeline

```
GitHub Push (main branch)
      │
      ├─── Frontend Tests
      │    └─── npm run build
      │         └─── Deploy to S3
      │              └─── Invalidate CloudFront Cache
      │
      └─── Backend Tests
           └─── Build Docker Image → ECR
                └─── Deploy to ECS (nrtaxai-backend-service)
                     └─── Run DB Migrations
```

### Infrastructure Provisioning

```
Terraform Apply
      │
      ├─── VPC + Subnets (Multi-AZ)
      ├─── S3 Bucket + CloudFront (Frontend)
      ├─── ECS Cluster (Backend only)
      ├─── RDS PostgreSQL (Multi-AZ)
      ├─── ElastiCache Redis
      ├─── S3 Buckets (uploads, pdfs, extracts)
      ├─── Lambda Functions
      ├─── WAF Rules
      └─── CloudWatch Alarms
```

## Summary

**Architecture**: S3 + CloudFront for frontend static assets, ECS Fargate for backend API
- **Cost-effective**: S3/CloudFront ~$5/month vs ECS ~$30/month
- **High performance**: Global CDN edge caching
- **Scalable**: Unlimited concurrent users
- **Simple**: Standard React deployment pattern
- **Reliable**: 99.99% SLA

Perfect for serving a React SPA while keeping the backend in a scalable container environment!
