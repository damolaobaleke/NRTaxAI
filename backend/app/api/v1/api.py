"""
API v1 Router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, 
    tax_compute, 
    users, 
    documents, tax_returns, chat,
    forms, operators, authorizations, audit, 
    monitoring,
    universities, partnerships, referrals, transactions,
    payouts, licenses, dashboards, tenant
)

api_router = APIRouter()

# Include all endpoint routers with proper prefixes 
api_router.include_router(monitoring.router, tags=["monitoring"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])  
api_router.include_router(tax_compute.router, prefix="/tax-compute", tags=["tax-computation"])  
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(tax_returns.router, prefix="/tax", tags=["tax-returns"])
api_router.include_router(forms.router, prefix="/forms", tags=["form-generation"])
api_router.include_router(operators.router, prefix="/operators", tags=["operators"])
api_router.include_router(authorizations.router, prefix="/authorizations", tags=["authorizations"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit-logs"])
# B2B endpoints
api_router.include_router(universities.router)
api_router.include_router(partnerships.router)
api_router.include_router(referrals.router)
api_router.include_router(transactions.router)
api_router.include_router(payouts.router)
api_router.include_router(licenses.router)
api_router.include_router(dashboards.router)
api_router.include_router(tenant.router)
