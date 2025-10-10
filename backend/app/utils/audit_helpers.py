"""
Audit Logging Helper Functions
Easy-to-use helpers for audit logging
"""

from typing import Dict, Any, Optional
import structlog

from app.services.audit_service import get_audit_service
from app.models.common import AuditAction, AuditActorType

logger = structlog.get_logger()


async def log_user_action(
    user_id: str,
    action: str,
    return_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
):
    """Log user action to audit trail"""
    try:
        audit_service = await get_audit_service()
        await audit_service.create_audit_log(
            actor_type=AuditActorType.USER.value,
            actor_id=user_id,
            return_id=return_id,
            action=action,
            payload=payload or {}
        )
    except Exception as e:
        logger.error("Failed to log user action", error=str(e))


async def log_operator_action(
    operator_id: str,
    action: str,
    return_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
):
    """Log operator action to audit trail"""
    try:
        audit_service = await get_audit_service()
        await audit_service.create_audit_log(
            actor_type=AuditActorType.OPERATOR.value,
            actor_id=operator_id,
            return_id=return_id,
            action=action,
            payload=payload or {}
        )
    except Exception as e:
        logger.error("Failed to log operator action", error=str(e))


async def log_system_action(
    action: str,
    return_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
):
    """Log system action to audit trail"""
    try:
        audit_service = await get_audit_service()
        await audit_service.create_audit_log(
            actor_type=AuditActorType.SYSTEM.value,
            actor_id=None,
            return_id=return_id,
            action=action,
            payload=payload or {}
        )
    except Exception as e:
        logger.error("Failed to log system action", error=str(e))


async def log_document_upload(user_id: str, document_id: str, doc_type: str, return_id: Optional[str] = None):
    """Log document upload"""
    await log_user_action(
        user_id=user_id,
        action=AuditAction.DOCUMENT_UPLOAD.value,
        return_id=return_id,
        payload={
            "document_id": document_id,
            "doc_type": doc_type
        }
    )


async def log_document_extracted(document_id: str, doc_type: str, return_id: Optional[str] = None):
    """Log document extraction completion"""
    await log_system_action(
        action=AuditAction.DOCUMENT_EXTRACTED.value,
        return_id=return_id,
        payload={
            "document_id": document_id,
            "doc_type": doc_type
        }
    )


async def log_tax_return_created(user_id: str, return_id: str, tax_year: int):
    """Log tax return creation"""
    await log_user_action(
        user_id=user_id,
        action=AuditAction.TAX_RETURN_CREATED.value,
        return_id=return_id,
        payload={
            "tax_year": tax_year
        }
    )


async def log_tax_return_computed(return_id: str, computation_result: Dict[str, Any]):
    """Log tax return computation"""
    await log_system_action(
        action=AuditAction.TAX_RETURN_COMPUTED.value,
        return_id=return_id,
        payload={
            "residency_status": computation_result.get("residency_determination", {}).get("residency_status"),
            "tax_liability": computation_result.get("final_computation", {}).get("tax_liability"),
            "ruleset_version": computation_result.get("ruleset_version")
        }
    )


async def log_review_approved(operator_id: str, return_id: str, comments: Optional[str] = None):
    """Log operator review approval"""
    await log_operator_action(
        operator_id=operator_id,
        action=AuditAction.REVIEW_APPROVED.value,
        return_id=return_id,
        payload={
            "decision": "approved",
            "comments": comments
        }
    )


async def log_review_rejected(operator_id: str, return_id: str, comments: Optional[str] = None):
    """Log operator review rejection"""
    await log_operator_action(
        operator_id=operator_id,
        action=AuditAction.REVIEW_REJECTED.value,
        return_id=return_id,
        payload={
            "decision": "rejected",
            "comments": comments
        }
    )


async def log_authorization_signed(user_id: str, authorization_id: str, return_id: str, signer_type: str):
    """Log Form 8879 signature"""
    await log_user_action(
        user_id=user_id,
        action=AuditAction.AUTHORIZATION_SIGNED.value,
        return_id=return_id,
        payload={
            "authorization_id": authorization_id,
            "signer_type": signer_type
        }
    )


async def log_form_generated(return_id: str, form_type: str, form_id: str):
    """Log form generation"""
    await log_system_action(
        action=AuditAction.FORM_GENERATED.value,
        return_id=return_id,
        payload={
            "form_id": form_id,
            "form_type": form_type
        }
    )


async def log_form_filed(return_id: str, form_type: str, irs_confirmation: Optional[str] = None):
    """Log form filing with IRS"""
    await log_system_action(
        action=AuditAction.FORM_FILED.value,
        return_id=return_id,
        payload={
            "form_type": form_type,
            "irs_confirmation": irs_confirmation
        }
    )
