"""
Authorization Service for Form 8879 Signatures
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
import structlog

from app.core.database import get_database
from sqlalchemy import text

logger = structlog.get_logger()


class AuthorizationService:
    """Service for handling Form 8879 authorizations"""
    
    def __init__(self, db):
        self.db = db
    
    async def get_pending_authorizations(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get pending authorizations for user
        
        Args:
            user_id: User ID
            
        Returns:
            List of pending authorizations
        """
        try:
            authorizations = await self.db.fetch_all(
                """
                SELECT 
                    a.id,
                    a.return_id,
                    a.form_type,
                    a.status,
                    a.expires_at,
                    a.created_at,
                    tr.tax_year
                FROM authorizations a
                JOIN tax_returns tr ON a.return_id = tr.id
                WHERE a.user_id = :user_id 
                AND a.status IN ('pending', 'user_signed')
                ORDER BY a.created_at DESC
                """,
                {"user_id": user_id}
            )
            
            auth_list = []
            for auth in authorizations:
                auth_list.append({
                    "authorization_id": str(auth["id"]),
                    "return_id": str(auth["return_id"]),
                    "form_type": auth["form_type"],
                    "status": auth["status"],
                    "tax_year": auth["tax_year"],
                    "expires_at": auth["expires_at"].isoformat() if auth["expires_at"] else None,
                    "created_at": auth["created_at"].isoformat() if auth["created_at"] else None
                })
            
            return auth_list
            
        except Exception as e:
            logger.error("Failed to get pending authorizations", error=str(e))
            raise Exception(f"Failed to get authorizations: {str(e)}")
    
    async def sign_authorization_taxpayer(
        self,
        authorization_id: str,
        user_id: str,
        pin: str,
        signature_method: str = "e-sign",
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Taxpayer signs Form 8879
        
        Args:
            authorization_id: Authorization ID
            user_id: User ID
            pin: 5-digit self-selected PIN
            signature_method: Signature method (e-sign, phone, wet-sign)
            ip_address: IP address of signer
            
        Returns:
            Signature result
        """
        try:
            logger.info("Taxpayer signing authorization", 
                       authorization_id=authorization_id,
                       user_id=user_id)
            
            # Validate PIN (must be 5 digits)
            if not pin or len(pin) != 5 or not pin.isdigit():
                raise ValueError("PIN must be exactly 5 digits")
            
            # Get authorization
            authorization = await self.db.fetch_one(
                """
                SELECT * FROM authorizations 
                WHERE id = :auth_id AND user_id = :user_id
                """,
                {"auth_id": authorization_id, "user_id": user_id}
            )
            
            if not authorization:
                raise ValueError("Authorization not found")
            
            if authorization["status"] != "pending":
                raise ValueError(f"Authorization already processed: {authorization['status']}")
            
            # Check expiration
            if authorization["expires_at"] and authorization["expires_at"] < datetime.utcnow():
                raise ValueError("Authorization has expired")
            
            # Hash PIN for storage (security)
            pin_hash = hashlib.sha256(pin.encode()).hexdigest()
            
            # Prepare signature data
            signature_data = {
                "taxpayer_pin_hash": pin_hash,
                "signature_method": signature_method,
                "ip_address": ip_address,
                "signed_at": datetime.utcnow().isoformat(),
                "user_agent": "NRTaxAI Web App"
            }
            
            # Update authorization
            await self.db.execute(
                """
                UPDATE authorizations 
                SET status = 'user_signed',
                    signature_method = :signature_method,
                    signature_data = :signature_data,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :auth_id
                """,
                {
                    "auth_id": authorization_id,
                    "signature_method": signature_method,
                    "signature_data": json.dumps(signature_data)
                }
            )
            
            logger.info("Taxpayer signature recorded", 
                       authorization_id=authorization_id)
            
            return {
                "authorization_id": authorization_id,
                "status": "user_signed",
                "next_step": "awaiting_preparer_signature",
                "signed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Taxpayer signature failed", error=str(e))
            raise Exception(f"Failed to sign authorization: {str(e)}")
    
    async def sign_authorization_operator(
        self,
        authorization_id: str,
        operator_id: str,
        pin: str
    ) -> Dict[str, Any]:
        """
        Operator/preparer signs Form 8879
        
        Args:
            authorization_id: Authorization ID
            operator_id: Operator ID (must have PTIN)
            pin: 5-digit ERO PIN
            
        Returns:
            Signature result
        """
        try:
            logger.info("Operator signing authorization", 
                       authorization_id=authorization_id,
                       operator_id=operator_id)
            
            # Validate PIN
            if not pin or len(pin) != 5 or not pin.isdigit():
                raise ValueError("PIN must be exactly 5 digits")
            
            # Get operator info
            operator = await self.db.fetch_one(
                "SELECT * FROM operators WHERE id = :operator_id",
                {"operator_id": operator_id}
            )
            
            if not operator:
                raise ValueError("Operator not found")
            
            if not operator.get("ptin"):
                raise ValueError("Operator must have valid PTIN")
            
            # Get authorization
            authorization = await self.db.fetch_one(
                "SELECT * FROM authorizations WHERE id = :auth_id",
                {"auth_id": authorization_id}
            )
            
            if not authorization:
                raise ValueError("Authorization not found")
            
            if authorization["status"] != "user_signed":
                raise ValueError(f"Cannot sign: authorization status is {authorization['status']}")
            
            # Hash PIN
            pin_hash = hashlib.sha256(pin.encode()).hexdigest()
            
            # Get existing signature data
            existing_signature_data = json.loads(authorization["signature_data"]) if authorization.get("signature_data") else {}
            
            # Add operator signature
            existing_signature_data["operator_pin_hash"] = pin_hash
            existing_signature_data["operator_id"] = operator_id
            existing_signature_data["operator_ptin"] = operator.get("ptin")
            existing_signature_data["operator_signed_at"] = datetime.utcnow().isoformat()
            
            # Update authorization to fully signed
            await self.db.execute(
                """
                UPDATE authorizations 
                SET status = 'signed',
                    signature_data = :signature_data,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :auth_id
                """,
                {
                    "auth_id": authorization_id,
                    "signature_data": json.dumps(existing_signature_data)
                }
            )
            
            # Update tax return status to ready for filing
            await self.db.execute(
                """
                UPDATE tax_returns 
                SET status = 'authorized'
                WHERE id = :return_id
                """,
                {"return_id": str(authorization["return_id"])}
            )
            
            logger.info("Operator signature recorded - authorization complete", 
                       authorization_id=authorization_id,
                       ptin=operator.get("ptin"))
            
            return {
                "authorization_id": authorization_id,
                "status": "signed",
                "return_status": "authorized",
                "next_step": "ready_for_efile",
                "signed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Operator signature failed", error=str(e))
            raise Exception(f"Failed to sign authorization: {str(e)}")
    
    async def get_authorization_status(
        self,
        authorization_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get authorization status
        
        Args:
            authorization_id: Authorization ID
            user_id: User ID for verification
            
        Returns:
            Authorization status
        """
        try:
            authorization = await self.db.fetch_one(
                """
                SELECT 
                    a.*,
                    tr.tax_year,
                    tr.status as return_status
                FROM authorizations a
                JOIN tax_returns tr ON a.return_id = tr.id
                WHERE a.id = :auth_id AND a.user_id = :user_id
                """,
                {"auth_id": authorization_id, "user_id": user_id}
            )
            
            if not authorization:
                raise ValueError("Authorization not found")
            
            signature_data = json.loads(authorization["signature_data"]) if authorization.get("signature_data") else {}
            
            return {
                "authorization_id": str(authorization["id"]),
                "return_id": str(authorization["return_id"]),
                "tax_year": authorization["tax_year"],
                "form_type": authorization["form_type"],
                "status": authorization["status"],
                "return_status": authorization["return_status"],
                "signature_method": authorization["signature_method"],
                "taxpayer_signed": "taxpayer_pin_hash" in signature_data,
                "operator_signed": "operator_pin_hash" in signature_data,
                "expires_at": authorization["expires_at"].isoformat() if authorization["expires_at"] else None,
                "created_at": authorization["created_at"].isoformat() if authorization["created_at"] else None
            }
            
        except Exception as e:
            logger.error("Failed to get authorization status", error=str(e))
            raise Exception(f"Failed to get authorization status: {str(e)}")
    
    async def revoke_authorization(
        self,
        authorization_id: str,
        user_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Revoke an authorization
        
        Args:
            authorization_id: Authorization ID
            user_id: User ID
            reason: Revocation reason
            
        Returns:
            Revocation result
        """
        try:
            logger.info("Revoking authorization", 
                       authorization_id=authorization_id,
                       reason=reason)
            
            # Get authorization
            authorization = await self.db.fetch_one(
                """
                SELECT * FROM authorizations 
                WHERE id = :auth_id AND user_id = :user_id
                """,
                {"auth_id": authorization_id, "user_id": user_id}
            )
            
            if not authorization:
                raise ValueError("Authorization not found")
            
            if authorization["status"] == "signed":
                raise ValueError("Cannot revoke signed authorization")
            
            # Update authorization
            await self.db.execute(
                """
                UPDATE authorizations 
                SET status = 'revoked',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :auth_id
                """,
                {"auth_id": authorization_id}
            )
            
            # Update tax return status back to approved
            await self.db.execute(
                """
                UPDATE tax_returns 
                SET status = 'approved'
                WHERE id = :return_id
                """,
                {"return_id": str(authorization["return_id"])}
            )
            
            logger.info("Authorization revoked", 
                       authorization_id=authorization_id)
            
            return {
                "authorization_id": authorization_id,
                "status": "revoked",
                "reason": reason,
                "revoked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Authorization revocation failed", error=str(e))
            raise Exception(f"Failed to revoke authorization: {str(e)}")


async def get_authorization_service():
    """Get authorization service instance"""
    db = await get_database()
    return AuthorizationService(db)
