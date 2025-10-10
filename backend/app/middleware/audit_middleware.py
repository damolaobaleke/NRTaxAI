"""
Audit Logging Middleware
Automatically logs all critical operations
"""

import json
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.services.audit_service import get_audit_service
from app.models.common import AuditAction

logger = structlog.get_logger()


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log auditable events"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Define which endpoints should be audited
        self.auditable_patterns = {
            "POST /api/v1/auth/login": AuditAction.USER_LOGIN.value,
            "POST /api/v1/auth/register": AuditAction.USER_REGISTER.value,
            "PUT /api/v1/users/me/profile": AuditAction.PROFILE_UPDATE.value,
            "POST /api/v1/documents/upload": AuditAction.DOCUMENT_UPLOAD.value,
            "POST /api/v1/tax/*/compute": AuditAction.TAX_RETURN_COMPUTED.value,
            "POST /api/v1/forms/*/generate": AuditAction.FORM_GENERATED.value,
            "POST /api/v1/operators/returns/*/review": AuditAction.REVIEW_APPROVED.value,
            "POST /api/v1/operators/returns/*/approve": AuditAction.REVIEW_APPROVED.value,
            "POST /api/v1/authorizations/*/sign/taxpayer": AuditAction.AUTHORIZATION_SIGNED.value,
            "POST /api/v1/authorizations/*/sign/operator": AuditAction.AUTHORIZATION_SIGNED.value
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log if auditable"""
        
        # Get request path and method
        path = request.url.path
        method = request.method
        
        # Process request
        response = await call_next(request)
        
        # Check if this endpoint should be audited
        should_audit = self._should_audit(method, path, response.status_code)
        
        if should_audit:
            try:
                # Extract user/operator ID from request state
                actor_type = getattr(request.state, "actor_type", "system")
                actor_id = getattr(request.state, "actor_id", None)
                return_id = getattr(request.state, "return_id", None)
                
                # Get action name
                action = self._get_action_name(method, path)
                
                # Build payload
                payload = {
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_agent": request.headers.get("user-agent"),
                    "ip_address": request.client.host if request.client else None
                }
                
                # Create audit log asynchronously (don't block response)
                try:
                    audit_service = await get_audit_service()
                    await audit_service.create_audit_log(
                        actor_type=actor_type,
                        actor_id=actor_id,
                        return_id=return_id,
                        action=action,
                        payload=payload
                    )
                except Exception as audit_error:
                    # Log error but don't fail the request
                    logger.error("Audit logging failed", error=str(audit_error))
                    
            except Exception as e:
                logger.error("Audit middleware error", error=str(e))
        
        return response
    
    def _should_audit(self, method: str, path: str, status_code: int) -> bool:
        """Determine if request should be audited"""
        # Only audit successful requests (2xx status codes)
        if status_code < 200 or status_code >= 300:
            return False
        
        # Check if path matches auditable patterns
        request_pattern = f"{method} {path}"
        
        for pattern in self.auditable_patterns.keys():
            if self._matches_pattern(request_pattern, pattern):
                return True
        
        return False
    
    def _matches_pattern(self, request: str, pattern: str) -> bool:
        """Check if request matches pattern (with wildcard support)"""
        if "*" in pattern:
            # Simple wildcard matching
            pattern_parts = pattern.split("*")
            if len(pattern_parts) == 2:
                return request.startswith(pattern_parts[0]) and request.endswith(pattern_parts[1])
        
        return request == pattern
    
    def _get_action_name(self, method: str, path: str) -> str:
        """Get action name for audit log"""
        request_pattern = f"{method} {path}"
        
        for pattern, action in self.auditable_patterns.items():
            if self._matches_pattern(request_pattern, pattern):
                return action
        
        # Default action name
        return f"{method}_{path.replace('/', '_')}"
