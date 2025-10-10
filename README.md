# NRTaxAI - AI-Powered Non-Resident Tax Preparation System

> **Enterprise-grade tax preparation and filing system for non-resident professionals and business owners on H1B, F-1, O-1, J-1, TN, E2, and other work visas.**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![AWS](https://img.shields.io/badge/AWS-Ready-orange.svg)](https://aws.amazon.com/)

## 🎯 Overview

NRTaxAI is a comprehensive, production-ready AI tax preparation system that combines:
- **Agentic AI** (GPT-4) for conversational tax assistance
- **Deterministic Tax Engine** for accurate calculations (no hallucinations)
- **AWS Textract** for document OCR and extraction
- **Human-in-the-Loop (HITL)** review by certified PTIN holders
- **IRS Compliance** with Publication 4557 standards
- **Enterprise Security** with KMS encryption, WAF, and audit logging

## 🌟 Key Features

### For Taxpayers
- 📄 **Upload Documents**: W-2, 1099-INT, 1099-NEC, 1098-T with automatic OCR
- 💬 **AI Chat Assistant**: Get instant answers to tax questions
- 🧮 **Automated Calculations**: Residency tests, treaty benefits, tax liability
- 📋 **Form Generation**: 1040-NR, 8843, W-8BEN, 1040-V as PDFs
- ✍️ **Electronic Signatures**: Sign Form 8879 online

### For PTIN Holders (Tax Professionals)
- 📊 **Review Dashboard**: Queue of returns awaiting review
- ✅ **Approve/Reject**: Review and approve tax returns
- 📝 **Request Revisions**: Send returns back with specific feedback
- 🔐 **Form 8879 Signing**: Add preparer signature for e-file

### For Administrators
- 📈 **Metrics & Monitoring**: Real-time system health
- 🔍 **Audit Logs**: Complete immutable audit trail
- 🛡️ **Security**: WAF, encryption, compliance tools
- 💾 **Backups**: Automated database and file backups

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/your-org/nrtaxai.git
cd nrtaxai

# Copy environment file
cp backend/env.example backend/.env
# Edit backend/.env with your AWS credentials

# Start all services
docker-compose up -d

# Initialize database
docker-compose exec backend python init_db.py

# Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Setup

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## 📖 Documentation

- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - Complete feature overview
- **[Database Guide](database-guide.md)** - SQL patterns and queries
- **[Document Upload](DOCUMENT_UPLOAD_README.md)** - Upload system details
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment
- **[Terraform Guide](terraform/README.md)** - Infrastructure as code

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   React     │────▶│   FastAPI    │────▶│   AWS       │
│   Frontend  │     │   Backend    │     │   Services  │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                     │
                           ▼                     ▼
                    ┌──────────────┐     ┌─────────────┐
                    │  PostgreSQL  │     │  Textract   │
                    │  (Multi-AZ)  │     │  S3/KMS     │
                    └──────────────┘     └─────────────┘
```

### Technology Stack

**Backend**
- FastAPI (Python 3.11)
- PostgreSQL 15 (Multi-AZ)
- Redis (ElastiCache)
- OpenAI GPT-4
- AWS Textract, S3, KMS, Lambda

**Frontend**
- React 18
- Material-UI
- Axios
- React Router

**Infrastructure**
- Terraform (IaC)
- Docker + Docker Compose
- AWS ECS Fargate
- AWS WAF
- GitHub Actions (CI/CD)

## 📋 System Requirements

### Development
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15
- Redis 7

### Production
- AWS Account
- Terraform 1.0+
- Domain name
- SSL certificate

## 🔐 Security & Compliance

### Security Features
- ✅ KMS envelope encryption for PII
- ✅ WAF with OWASP Top 10 protection
- ✅ Immutable audit logs with hash chaining
- ✅ Antivirus scanning (AWS Lambda)
- ✅ Row-level security in database
- ✅ Rate limiting and DDoS protection
- ✅ Secrets management (AWS Secrets Manager)

### Compliance
- ✅ IRS Publication 4557 standards
- ✅ HITL (Human-in-the-Loop) review required
- ✅ PTIN holder verification
- ✅ Form 8879 dual signatures
- ✅ Complete audit trail
- ✅ Data retention policies

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest --cov=app

# Frontend tests
cd frontend
npm test

# Security scan
trivy fs .

# Load testing
locust -f tests/load_test.py
```

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token

### Documents
- `POST /api/v1/documents/upload` - Request upload URL
- `POST /api/v1/documents/{id}/confirm` - Confirm upload
- `POST /api/v1/documents/{id}/start` - Start extraction

### Tax Computation
- `POST /api/v1/tax/{return_id}/compute` - Compute taxes
- `GET /api/v1/tax/{return_id}/summary` - Get summary

### Forms
- `POST /api/v1/forms/{return_id}/generate` - Generate forms
- `GET /api/v1/forms/{return_id}/forms` - List forms

### Operator Review
- `GET /api/v1/operators/queue` - Review queue
- `POST /api/v1/operators/returns/{id}/approve` - Approve return

Full API documentation: http://localhost:8000/docs

## 🤝 Contributing

This is a private project for non-resident tax preparation. Contributions require:
1. Background check
2. Tax law knowledge
3. Security clearance
4. Legal agreements

## 📄 License

Proprietary - All Rights Reserved

## ⚠️ Legal Disclaimer

This software is provided for tax preparation assistance only. Users should:
- Consult with licensed tax professionals
- Verify all calculations
- Understand their tax obligations
- Review all forms before signing

NRTaxAI is not a substitute for professional tax advice.

## 📞 Support

- **Email**: support@nrtaxai.com
- **Documentation**: https://docs.nrtaxai.com
- **Issues**: https://github.com/your-org/nrtaxai/issues

---

**Built with ❤️ for non-resident professionals navigating US tax compliance**