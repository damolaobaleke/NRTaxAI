"""
Operator Service for PTIN Holder Reviews
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
import structlog

from app.core.database import get_database
from app.utils.audit_helpers import log_operator_action, log_review_approved, log_review_rejected
from sqlalchemy import text

logger = structlog.get_logger()


class OperatorService:
    """Service for operator (PTIN holder) review operations"""
    
    def __init__(self, db):
        self.db = db
    
    async def get_review_queue(
        self,
        operator_id: str,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get review queue for operator"""
        try:
            logger.info("Fetching review queue", operator_id=operator_id)
            
            query = """
                SELECT 
                    tr.id, tr.tax_year, tr.status, tr.created_at, tr.updated_at,
                    u.email as taxpayer_email,
                    up.first_name, up.last_name, up.visa_class, up.residency_country,
                    (SELECT COUNT(*) FROM documents WHERE return_id = tr.id) as document_count,
                    (SELECT COUNT(*) FROM forms WHERE return_id = tr.id) as form_count
                FROM tax_returns tr
                JOIN users u ON tr.user_id = u.id
                LEFT JOIN user_profiles up ON up.user_id = u.id
                WHERE tr.status IN ('review', 'needs_revision')
            """
            
            params = {}
            if status_filter:
                query += " AND tr.status = :status_filter"
                params["status_filter"] = status_filter
            
            query += " ORDER BY tr.created_at ASC"
            
            returns = await self.db.fetch_all(query, params)
            
            queue = []
            for return_data in returns:
                queue.append({
                    "return_id": str(return_data["id"]),
                    "tax_year": return_data["tax_year"],
                    "status": return_data["status"],
                    "taxpayer": {
                        "email": return_data["taxpayer_email"],
                        "first_name": return_data["first_name"],
                        "last_name": return_data["last_name"],
                        "visa_class": return_data["visa_class"],
                        "country": return_data["residency_country"]
                    },
                    "document_count": return_data["document_count"],
                    "form_count": return_data["form_count"],
                    "submitted_at": return_data["created_at"].isoformat() if return_data["created_at"] else None
                })
            
            return queue
            
        except Exception as e:
            logger.error("Failed to fetch review queue", error=str(e))
            raise Exception(f"Failed to get review queue: {str(e)}")
    
    async def get_return_for_review(self, return_id: str, operator_id: str) -> Dict[str, Any]:
        """Get complete tax return details for review"""
        try:
            tax_return = await self.db.fetch_one(
                """
                SELECT tr.*, u.email as taxpayer_email, up.*
                FROM tax_returns tr
                JOIN users u ON tr.user_id = u.id
                LEFT JOIN user_profiles up ON up.user_id = u.id
                WHERE tr.id = :return_id
                """,
                {"return_id": return_id}
            )
            
            if not tax_return:
                raise ValueError("Tax return not found")
            
            documents = await self.db.fetch_all(
                "SELECT * FROM documents WHERE return_id = :return_id",
                {"return_id": return_id}
            )
            
            forms = await self.db.fetch_all(
                "SELECT * FROM forms WHERE return_id = :return_id",
                {"return_id": return_id}
            )
            
            return {
                "return_id": str(tax_return["id"]),
                "tax_year": tax_return["tax_year"],
                "status": tax_return["status"],
                "taxpayer": {
                    "email": tax_return["taxpayer_email"],
                    "first_name": tax_return.get("first_name"),
                    "last_name": tax_return.get("last_name"),
                    "visa_class": tax_return.get("visa_class")
                },
                "documents": [{"id": str(d["id"]), "type": d["doc_type"]} for d in documents],
                "forms": [{"id": str(f["id"]), "type": f["form_type"]} for f in forms]
            }
            
        except Exception as e:
            logger.error("Failed to get return for review", error=str(e))
            raise Exception(f"Failed to get return: {str(e)}")
    
    async def submit_review(self, return_id: str, operator_id: str, decision: str, 
                           comments: Optional[str] = None, diffs: Optional[Dict] = None) -> Dict[str, Any]:
        """Submit operator review decision"""
        try:
            review = await self.db.fetch_one(
                """
                INSERT INTO reviews (return_id, operator_id, decision, comments, diffs_json)
                VALUES (:return_id, :operator_id, :decision, :comments, :diffs)
                RETURNING id, created_at
                """,
                {
                    "return_id": return_id,
                    "operator_id": operator_id,
                    "decision": decision,
                    "comments": comments,
                    "diffs": json.dumps(diffs) if diffs else None
                }
            )
            
            new_status = {"approved": "approved", "rejected": "rejected", "needs_revision": "needs_revision"}[decision]
            
            await self.db.execute(
                "UPDATE tax_returns SET status = :status WHERE id = :return_id",
                {"return_id": return_id, "status": new_status}
            )
            
            # Log audit
            if decision == "approved":
                await log_review_approved(operator_id, return_id, comments)
            elif decision == "rejected":
                await log_review_rejected(operator_id, return_id, comments)
            
            return {
                "review_id": str(review["id"]),
                "return_id": return_id,
                "decision": decision,
                "new_status": new_status
            }
            
        except Exception as e:
            logger.error("Failed to submit review", error=str(e))
            raise Exception(f"Failed to submit review: {str(e)}")
    
    async def approve_return(self, return_id: str, operator_id: str, comments: Optional[str] = None) -> Dict[str, Any]:
        """Approve return and generate Form 8879"""
        try:
            review = await self.submit_review(return_id, operator_id, "approved", comments)
            
            tax_return = await self.db.fetch_one(
                "SELECT user_id FROM tax_returns WHERE id = :return_id",
                {"return_id": return_id}
            )
            
            authorization = await self.db.fetch_one(
                """
                INSERT INTO authorizations (return_id, user_id, form_type, status, expires_at)
                VALUES (:return_id, :user_id, '8879', 'pending', :expires_at)
                RETURNING id
                """,
                {
                    "return_id": return_id,
                    "user_id": str(tax_return["user_id"]),
                    "expires_at": datetime.utcnow() + timedelta(days=30)
                }
            )
            
            return {
                "review_id": review["review_id"],
                "authorization_id": str(authorization["id"]),
                "status": "approved"
            }
            
        except Exception as e:
            logger.error("Failed to approve return", error=str(e))
            raise Exception(f"Failed to approve: {str(e)}")
    
    async def request_revision(self, return_id: str, operator_id: str, 
                              revision_items: List[Dict], comments: str) -> Dict[str, Any]:
        """Request revisions"""
        try:
            review = await self.submit_review(
                return_id, operator_id, "needs_revision", comments, 
                {"revision_items": revision_items}
            )
            
            for item in revision_items:
                await self.db.execute(
                    """
                    INSERT INTO validations (return_id, rule_code, message, severity, field_path)
                    VALUES (:return_id, :rule_code, :message, :severity, :field_path)
                    """,
                    {
                        "return_id": return_id,
                        "rule_code": item.get("rule_code", "OPERATOR_REVIEW"),
                        "message": item.get("message", "Revision needed"),
                        "severity": item.get("severity", "warning"),
                        "field_path": item.get("field_path")
                    }
                )
            
            return review
            
        except Exception as e:
            logger.error("Failed to request revision", error=str(e))
            raise Exception(f"Failed to request revision: {str(e)}")
    
    async def get_operator_stats(self, operator_id: str) -> Dict[str, Any]:
        """Get operator statistics"""
        try:
            stats = await self.db.fetch_one(
                """
                SELECT 
                    COUNT(*) as total_reviews,
                    COUNT(CASE WHEN decision = 'approved' THEN 1 END) as approved_count,
                    COUNT(CASE WHEN decision = 'rejected' THEN 1 END) as rejected_count
                FROM reviews WHERE operator_id = :operator_id
                """,
                {"operator_id": operator_id}
            )
            
            pending = await self.db.fetch_one(
                "SELECT COUNT(*) as count FROM tax_returns WHERE status IN ('review', 'needs_revision')",
                {}
            )
            
            return {
                "total_reviews": stats["total_reviews"],
                "approved": stats["approved_count"],
                "rejected": stats["rejected_count"],
                "pending_review": pending["count"]
            }
            
        except Exception as e:
            logger.error("Failed to get stats", error=str(e))
            raise Exception(f"Failed to get stats: {str(e)}")


async def get_operator_service():
    """Get operator service instance"""
    db = await get_database()
    return OperatorService(db)
