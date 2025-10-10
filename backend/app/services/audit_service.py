"""
Audit Service - Immutable Audit Logs with Hash Chaining
"""

import json
import hashlib
import csv
import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
import structlog

from app.core.database import get_database
from app.services.s3_service import s3_service
from app.core.config import settings

logger = structlog.get_logger()


class AuditService:
    """Service for managing immutable audit logs with hash chaining"""
    
    def __init__(self, db):
        self.db = db
    
    async def create_audit_log(
        self,
        actor_type: str,
        actor_id: Optional[str],
        return_id: Optional[str],
        action: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an immutable audit log entry with hash chaining
        
        Args:
            actor_type: Type of actor (user, operator, system)
            actor_id: Actor's ID
            return_id: Related tax return ID
            action: Action performed
            payload: Action payload/details
            
        Returns:
            Created audit log entry
        """
        try:
            logger.info("Creating audit log", 
                       actor_type=actor_type,
                       action=action)
            
            # Get previous hash for chain
            previous_hash = await self._get_previous_hash(return_id)
            
            # Compute current hash
            log_data = {
                'actor_type': actor_type,
                'actor_id': actor_id,
                'return_id': return_id,
                'action': action,
                'payload': payload,
                'previous_hash': previous_hash,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            current_hash = hashlib.sha256(
                json.dumps(log_data, sort_keys=True).encode()
            ).hexdigest()
            
            # Insert audit log
            audit_log = await self.db.fetch_one(
                """
                INSERT INTO audit_logs (
                    actor_type, actor_id, return_id, action, payload_json, hash
                )
                VALUES (
                    :actor_type, :actor_id, :return_id, :action, :payload, :hash
                )
                RETURNING id, created_at
                """,
                {
                    'actor_type': actor_type,
                    'actor_id': actor_id,
                    'return_id': return_id,
                    'action': action,
                    'payload': json.dumps(payload),
                    'hash': current_hash
                }
            )
            
            logger.info("Audit log created", 
                       audit_log_id=str(audit_log["id"]),
                       hash=current_hash)
            
            return {
                "audit_log_id": str(audit_log["id"]),
                "hash": current_hash,
                "previous_hash": previous_hash,
                "created_at": audit_log["created_at"].isoformat() if audit_log["created_at"] else None
            }
            
        except Exception as e:
            logger.error("Failed to create audit log", error=str(e))
            raise Exception(f"Failed to create audit log: {str(e)}")
    
    async def _get_previous_hash(self, return_id: Optional[str]) -> str:
        """Get the hash of the previous audit log entry"""
        try:
            if not return_id:
                return '0' * 64  # Genesis hash for first entry
            
            previous_log = await self.db.fetch_one(
                """
                SELECT hash FROM audit_logs 
                WHERE return_id = :return_id 
                ORDER BY created_at DESC 
                LIMIT 1
                """,
                {"return_id": return_id}
            )
            
            if previous_log:
                return previous_log['hash']
            else:
                return '0' * 64  # Genesis hash
                
        except Exception as e:
            logger.error("Failed to get previous hash", error=str(e))
            return '0' * 64
    
    async def verify_audit_chain(
        self,
        return_id: str
    ) -> Dict[str, Any]:
        """
        Verify the integrity of the audit log chain
        
        Args:
            return_id: Tax return ID
            
        Returns:
            Verification result
        """
        try:
            logger.info("Verifying audit chain", return_id=return_id)
            
            # Get all audit logs for return
            audit_logs = await self.db.fetch_all(
                """
                SELECT 
                    id,
                    actor_type,
                    actor_id,
                    return_id,
                    action,
                    payload_json,
                    hash,
                    created_at
                FROM audit_logs
                WHERE return_id = :return_id
                ORDER BY created_at ASC
                """,
                {"return_id": return_id}
            )
            
            if not audit_logs:
                return {
                    "valid": True,
                    "message": "No audit logs found",
                    "total_logs": 0
                }
            
            verification_results = []
            previous_hash = '0' * 64
            
            for log in audit_logs:
                # Reconstruct log data
                log_data = {
                    'actor_type': log['actor_type'],
                    'actor_id': str(log['actor_id']) if log['actor_id'] else None,
                    'return_id': str(log['return_id']) if log['return_id'] else None,
                    'action': log['action'],
                    'payload': json.loads(log['payload_json']) if log['payload_json'] else {},
                    'previous_hash': previous_hash,
                    'timestamp': log['created_at'].isoformat() if log['created_at'] else None
                }
                
                # Compute expected hash
                computed_hash = hashlib.sha256(
                    json.dumps(log_data, sort_keys=True).encode()
                ).hexdigest()
                
                # Verify hash matches
                is_valid = computed_hash == log['hash']
                
                verification_results.append({
                    "log_id": str(log['id']),
                    "action": log['action'],
                    "stored_hash": log['hash'],
                    "computed_hash": computed_hash,
                    "valid": is_valid,
                    "timestamp": log['created_at'].isoformat() if log['created_at'] else None
                })
                
                # Update previous hash for next iteration
                previous_hash = log['hash']
            
            # Check if all logs are valid
            all_valid = all(result['valid'] for result in verification_results)
            
            logger.info("Audit chain verification completed", 
                       return_id=return_id,
                       total_logs=len(audit_logs),
                       all_valid=all_valid)
            
            return {
                "valid": all_valid,
                "total_logs": len(audit_logs),
                "verification_results": verification_results,
                "verified_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Audit chain verification failed", error=str(e))
            raise Exception(f"Failed to verify audit chain: {str(e)}")
    
    async def export_audit_trail(
        self,
        return_id: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export complete audit trail for a tax return
        
        Args:
            return_id: Tax return ID
            format: Export format (json, csv)
            
        Returns:
            Export result with download URL
        """
        try:
            logger.info("Exporting audit trail", 
                       return_id=return_id,
                       format=format)
            
            # Get complete audit trail
            audit_logs = await self.db.fetch_all(
                """
                SELECT 
                    al.id,
                    al.actor_type,
                    al.actor_id,
                    al.action,
                    al.payload_json,
                    al.hash,
                    al.created_at,
                    CASE 
                        WHEN al.actor_type = 'user' THEN u.email
                        WHEN al.actor_type = 'operator' THEN o.email
                        ELSE 'system'
                    END AS actor_email
                FROM audit_logs al
                LEFT JOIN users u ON al.actor_type = 'user' AND al.actor_id = u.id
                LEFT JOIN operators o ON al.actor_type = 'operator' AND al.actor_id = o.id
                WHERE al.return_id = :return_id
                ORDER BY al.created_at ASC
                """,
                {"return_id": return_id}
            )
            
            # Verify chain integrity
            verification = await self.verify_audit_chain(return_id)
            
            # Export in requested format
            if format == "json":
                export_content = await self._export_as_json(audit_logs, verification)
                content_type = "application/json"
                file_extension = "json"
            elif format == "csv":
                export_content = await self._export_as_csv(audit_logs, verification)
                content_type = "text/csv"
                file_extension = "csv"
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            # Upload to S3
            file_key = f"audit-trails/{return_id}/audit_trail_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
            
            upload_result = await s3_service.upload_file(
                file_key=file_key,
                file_content=export_content.encode('utf-8'),
                bucket=settings.S3_BUCKET_EXTRACTS,
                metadata={
                    "return_id": return_id,
                    "export_format": format,
                    "exported_at": datetime.utcnow().isoformat(),
                    "chain_valid": str(verification["valid"])
                }
            )
            
            # Generate download URL
            download_url = await s3_service.generate_presigned_download_url(
                file_key=file_key,
                bucket=settings.S3_BUCKET_EXTRACTS,
                expires_in=3600
            )
            
            logger.info("Audit trail exported", 
                       return_id=return_id,
                       format=format,
                       file_key=file_key)
            
            return {
                "return_id": return_id,
                "file_key": file_key,
                "format": format,
                "download_url": download_url,
                "total_logs": len(audit_logs),
                "chain_valid": verification["valid"],
                "exported_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Audit trail export failed", error=str(e))
            raise Exception(f"Failed to export audit trail: {str(e)}")
    
    async def _export_as_json(
        self,
        audit_logs: List,
        verification: Dict[str, Any]
    ) -> str:
        """Export audit logs as JSON"""
        export_data = {
            "metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "total_logs": len(audit_logs),
                "chain_valid": verification["valid"]
            },
            "verification": verification,
            "audit_logs": []
        }
        
        for log in audit_logs:
            export_data["audit_logs"].append({
                "id": str(log["id"]),
                "actor_type": log["actor_type"],
                "actor_id": str(log["actor_id"]) if log["actor_id"] else None,
                "actor_email": log.get("actor_email"),
                "action": log["action"],
                "payload": json.loads(log["payload_json"]) if log["payload_json"] else {},
                "hash": log["hash"],
                "timestamp": log["created_at"].isoformat() if log["created_at"] else None
            })
        
        return json.dumps(export_data, indent=2)
    
    async def _export_as_csv(
        self,
        audit_logs: List,
        verification: Dict[str, Any]
    ) -> str:
        """Export audit logs as CSV"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Timestamp',
            'Actor Type',
            'Actor Email',
            'Action',
            'Payload',
            'Hash',
            'Chain Valid'
        ])
        
        # Write data
        for log in audit_logs:
            writer.writerow([
                log["created_at"].isoformat() if log["created_at"] else "",
                log["actor_type"],
                log.get("actor_email", ""),
                log["action"],
                log["payload_json"] or "",
                log["hash"],
                "Yes" if verification["valid"] else "No"
            ])
        
        return output.getvalue()
    
    async def get_audit_logs_for_return(
        self,
        return_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get audit logs for a tax return
        
        Args:
            return_id: Tax return ID
            limit: Maximum number of logs to return
            offset: Offset for pagination
            
        Returns:
            Audit logs with metadata
        """
        try:
            # Get total count
            count_result = await self.db.fetch_one(
                "SELECT COUNT(*) as count FROM audit_logs WHERE return_id = :return_id",
                {"return_id": return_id}
            )
            
            total_count = count_result["count"]
            
            # Get logs with pagination
            logs = await self.db.fetch_all(
                """
                SELECT 
                    al.id,
                    al.actor_type,
                    al.action,
                    al.payload_json,
                    al.hash,
                    al.created_at,
                    CASE 
                        WHEN al.actor_type = 'user' THEN u.email
                        WHEN al.actor_type = 'operator' THEN o.email
                        ELSE 'system'
                    END AS actor_email
                FROM audit_logs al
                LEFT JOIN users u ON al.actor_type = 'user' AND al.actor_id = u.id
                LEFT JOIN operators o ON al.actor_type = 'operator' AND al.actor_id = o.id
                WHERE al.return_id = :return_id
                ORDER BY al.created_at DESC
                LIMIT :limit OFFSET :offset
                """,
                {"return_id": return_id, "limit": limit, "offset": offset}
            )
            
            log_list = []
            for log in logs:
                log_list.append({
                    "id": str(log["id"]),
                    "actor_type": log["actor_type"],
                    "actor_email": log.get("actor_email"),
                    "action": log["action"],
                    "payload": json.loads(log["payload_json"]) if log["payload_json"] else {},
                    "hash": log["hash"],
                    "timestamp": log["created_at"].isoformat() if log["created_at"] else None
                })
            
            return {
                "return_id": return_id,
                "logs": log_list,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
            
        except Exception as e:
            logger.error("Failed to get audit logs", error=str(e))
            raise Exception(f"Failed to get audit logs: {str(e)}")
    
    async def get_system_audit_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        actor_type: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get system-wide audit logs with filters
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            actor_type: Filter by actor type
            action: Filter by action
            limit: Maximum results
            
        Returns:
            Filtered audit logs
        """
        try:
            query = """
                SELECT 
                    al.id,
                    al.actor_type,
                    al.action,
                    al.payload_json,
                    al.hash,
                    al.created_at,
                    al.return_id,
                    CASE 
                        WHEN al.actor_type = 'user' THEN u.email
                        WHEN al.actor_type = 'operator' THEN o.email
                        ELSE 'system'
                    END AS actor_email
                FROM audit_logs al
                LEFT JOIN users u ON al.actor_type = 'user' AND al.actor_id = u.id
                LEFT JOIN operators o ON al.actor_type = 'operator' AND al.actor_id = o.id
                WHERE 1=1
            """
            
            params = {}
            
            if start_date:
                query += " AND al.created_at >= :start_date"
                params["start_date"] = start_date
            
            if end_date:
                query += " AND al.created_at <= :end_date"
                params["end_date"] = end_date
            
            if actor_type:
                query += " AND al.actor_type = :actor_type"
                params["actor_type"] = actor_type
            
            if action:
                query += " AND al.action = :action"
                params["action"] = action
            
            query += " ORDER BY al.created_at DESC LIMIT :limit"
            params["limit"] = limit
            
            logs = await self.db.fetch_all(query, params)
            
            log_list = []
            for log in logs:
                log_list.append({
                    "id": str(log["id"]),
                    "actor_type": log["actor_type"],
                    "actor_email": log.get("actor_email"),
                    "action": log["action"],
                    "payload": json.loads(log["payload_json"]) if log["payload_json"] else {},
                    "hash": log["hash"],
                    "return_id": str(log["return_id"]) if log["return_id"] else None,
                    "timestamp": log["created_at"].isoformat() if log["created_at"] else None
                })
            
            return log_list
            
        except Exception as e:
            logger.error("Failed to get system audit logs", error=str(e))
            raise Exception(f"Failed to get system audit logs: {str(e)}")
    
    async def create_audit_bundle(
        self,
        return_id: str
    ) -> Dict[str, Any]:
        """
        Create complete audit bundle for tax return
        Includes all documents, forms, audit logs, and verification
        
        Args:
            return_id: Tax return ID
            
        Returns:
            Audit bundle metadata
        """
        try:
            logger.info("Creating audit bundle", return_id=return_id)
            
            # Get tax return data
            tax_return = await self.db.fetch_one(
                """
                SELECT 
                    tr.*,
                    u.email as taxpayer_email,
                    up.first_name,
                    up.last_name,
                    up.visa_class,
                    up.residency_country
                FROM tax_returns tr
                JOIN users u ON tr.user_id = u.id
                LEFT JOIN user_profiles up ON up.user_id = u.id
                WHERE tr.id = :return_id
                """,
                {"return_id": return_id}
            )
            
            if not tax_return:
                raise ValueError("Tax return not found")
            
            # Get all related data
            documents = await self.db.fetch_all(
                "SELECT * FROM documents WHERE return_id = :return_id",
                {"return_id": return_id}
            )
            
            forms = await self.db.fetch_all(
                "SELECT * FROM forms WHERE return_id = :return_id",
                {"return_id": return_id}
            )
            
            reviews = await self.db.fetch_all(
                """
                SELECT 
                    r.*,
                    o.email as operator_email,
                    o.ptin
                FROM reviews r
                JOIN operators o ON r.operator_id = o.id
                WHERE r.return_id = :return_id
                """,
                {"return_id": return_id}
            )
            
            authorizations = await self.db.fetch_all(
                "SELECT * FROM authorizations WHERE return_id = :return_id",
                {"return_id": return_id}
            )
            
            # Get audit logs
            audit_logs_result = await self.get_audit_logs_for_return(
                return_id=return_id,
                limit=1000
            )
            
            # Verify audit chain
            verification = await self.verify_audit_chain(return_id)
            
            # Create bundle
            bundle = {
                "metadata": {
                    "return_id": return_id,
                    "tax_year": tax_return["tax_year"],
                    "taxpayer": {
                        "email": tax_return["taxpayer_email"],
                        "first_name": tax_return["first_name"],
                        "last_name": tax_return["last_name"],
                        "visa_class": tax_return["visa_class"],
                        "country": tax_return["residency_country"]
                    },
                    "bundle_created_at": datetime.utcnow().isoformat(),
                    "chain_verified": verification["valid"]
                },
                "tax_return": {
                    "id": str(tax_return["id"]),
                    "tax_year": tax_return["tax_year"],
                    "status": tax_return["status"],
                    "ruleset_version": tax_return["ruleset_version"],
                    "created_at": tax_return["created_at"].isoformat() if tax_return["created_at"] else None,
                    "updated_at": tax_return["updated_at"].isoformat() if tax_return["updated_at"] else None
                },
                "documents": [
                    {
                        "id": str(doc["id"]),
                        "type": doc["doc_type"],
                        "status": doc["status"],
                        "s3_key": doc["s3_key"],
                        "uploaded_at": doc["created_at"].isoformat() if doc["created_at"] else None
                    }
                    for doc in documents
                ],
                "forms": [
                    {
                        "id": str(form["id"]),
                        "type": form["form_type"],
                        "s3_key": form["s3_key"],
                        "version": form["version"],
                        "generated_at": form["created_at"].isoformat() if form["created_at"] else None
                    }
                    for form in forms
                ],
                "reviews": [
                    {
                        "id": str(review["id"]),
                        "decision": review["decision"],
                        "comments": review["comments"],
                        "operator_email": review["operator_email"],
                        "operator_ptin": review["ptin"],
                        "reviewed_at": review["created_at"].isoformat() if review["created_at"] else None
                    }
                    for review in reviews
                ],
                "authorizations": [
                    {
                        "id": str(auth["id"]),
                        "form_type": auth["form_type"],
                        "status": auth["status"],
                        "created_at": auth["created_at"].isoformat() if auth["created_at"] else None
                    }
                    for auth in authorizations
                ],
                "audit_logs": audit_logs_result["logs"],
                "chain_verification": verification
            }
            
            # Save bundle to S3
            bundle_json = json.dumps(bundle, indent=2)
            bundle_key = f"audit-bundles/{return_id}/bundle_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            
            await s3_service.upload_file(
                file_key=bundle_key,
                file_content=bundle_json.encode('utf-8'),
                bucket=settings.S3_BUCKET_EXTRACTS,
                metadata={
                    "return_id": return_id,
                    "bundle_type": "complete_audit",
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # Generate download URL
            bundle_download_url = await s3_service.generate_presigned_download_url(
                file_key=bundle_key,
                bucket=settings.S3_BUCKET_EXTRACTS,
                expires_in=3600
            )
            
            logger.info("Audit bundle created", 
                       return_id=return_id,
                       bundle_key=bundle_key)
            
            return {
                "bundle_key": bundle_key,
                "download_url": bundle_download_url,
                "bundle_size_bytes": len(bundle_json),
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to create audit bundle", error=str(e))
            raise Exception(f"Failed to create audit bundle: {str(e)}")


async def get_audit_service():
    """Get audit service instance"""
    db = await get_database()
    return AuditService(db)
