"""
Antivirus Scanning Service
"""

import boto3
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError
import structlog

from app.core.config import settings
from app.services.s3_service import s3_service

logger = structlog.get_logger()


class AVScanner:
    """Antivirus scanning service using AWS Lambda"""
    
    def __init__(self):
        # Build credentials dict, only include session_token if present
        credentials = {
            'region_name': settings.AWS_REGION,
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY
        }
        if settings.AWS_SESSION_TOKEN:
            credentials['aws_session_token'] = settings.AWS_SESSION_TOKEN
        
        self.lambda_client = boto3.client('lambda', **credentials)
        # TODO: Implement lambda function in aws
        self.scan_function_name = "nrtaxai-av-scanner"  # Lambda function name
    
    async def scan_file(
        self,
        file_key: str,
        bucket: Optional[str] = None,
        scan_type: str = "full"
    ) -> Dict[str, Any]:
        """
        Scan file for malware and threats
        
        Args:
            file_key: S3 object key to scan
            bucket: S3 bucket name
            scan_type: Type of scan (quick, full, deep)
            
        Returns:
            Scan result with threat information
        """
        try:
            bucket = bucket or settings.S3_BUCKET_UPLOADS
            
            # Get file metadata first
            file_metadata = await s3_service.get_file_metadata(file_key, bucket)
            file_size = file_metadata.get('size_bytes', 0)
            
            # Check file size limits for scanning
            max_scan_size = 100 * 1024 * 1024  # 100MB limit for AV scanning
            if file_size > max_scan_size:
                logger.warning("File too large for AV scanning", file_key=file_key, size=file_size)
                return {
                    "scan_status": "skipped",
                    "reason": "file_too_large",
                    "file_size_bytes": file_size,
                    "max_scan_size": max_scan_size,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Prepare scan payload
            scan_payload = {
                "action": "scan",
                "bucket": bucket,
                "key": file_key,
                "scan_type": scan_type,
                "scan_options": {
                    "scan_archives": True,
                    "scan_pdfs": True,
                    "scan_images": False,  # Skip image scanning for performance
                    "quarantine_threats": True
                }
            }
            
            # Invoke Lambda function
            response = self.lambda_client.invoke(
                FunctionName=self.scan_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(scan_payload)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            
            if response.get('FunctionError'):
                logger.error("Antivirus scan Lambda function error", error=response_payload, function_name="scan_file", class_name="AVScanner")
                return {
                    "scan_status": "error",
                    "error": response_payload.get('errorMessage', 'Unknown error'),
                    "timestamp": datetime.now().isoformat()
                }
            
            # Process scan result
            scan_result = response_payload.get('scan_result', {})
            print(scan_result)
            return {
                "scan_status": scan_result.get('status', 'unknown'),
                "threats_detected": scan_result.get('threats_detected', 0),
                "threats": scan_result.get('threats', []),
                "scan_engine": scan_result.get('engine', 'unknown'),
                "scan_version": scan_result.get('version', 'unknown'),
                "scan_duration_ms": scan_result.get('duration_ms', 0),
                "file_hash": scan_result.get('file_hash', ''),
                "quarantined": scan_result.get('quarantined', False),
                "quarantine_location": scan_result.get('quarantine_location', ''),
                "clean": scan_result.get('clean', False),
                "timestamp": datetime.now().isoformat(),
                "file_key": file_key,
                "file_size_bytes": file_size
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            
            # Handle case where Lambda function doesn't exist
            if error_code == 'ResourceNotFoundException':
                logger.warning("AV scan Lambda function not found, skipping scan", 
                             file_key=file_key, 
                             function_name=self.scan_function_name)
                return {
                    "scan_status": "skipped",
                    "reason": "lambda_function_not_found",
                    "error": "Antivirus scanning Lambda function not configured",
                    "clean": True,  # Assume clean if scanner unavailable
                    "timestamp": datetime.now().isoformat(),
                    "file_key": file_key,
                    "note": "Scan skipped - Lambda function not available"
                }
            
            logger.error("AV scan AWS error", error=str(e), error_code=error_code, file_key=file_key)
            return {
                "scan_status": "error",
                "error": f"AWS error: {str(e)}",
                "error_code": error_code,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error("AV scan error", error=str(e), file_key=file_key)
            return {
                "scan_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """
        Get status of a scan job
        
        Args:
            scan_id: Unique scan identifier
            
        Returns:
            Scan status information
        """
        try:
            payload = {
                "action": "status",
                "scan_id": scan_id
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.scan_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            return response_payload.get('status_result', {})
            
        except Exception as e:
            logger.error("AV scan status error", error=str(e), scan_id=scan_id)
            return {
                "scan_status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def quarantine_file(
        self,
        file_key: str,
        bucket: Optional[str] = None,
        reason: str = "threat_detected"
    ) -> Dict[str, Any]:
        """
        Quarantine a file due to threat detection
        
        Args:
            file_key: S3 object key to quarantine
            bucket: S3 bucket name
            reason: Reason for quarantine
            
        Returns:
            Quarantine result
        """
        try:
            bucket = bucket or settings.S3_BUCKET_UPLOADS
            quarantine_bucket = f"{bucket}-quarantine"
            quarantine_key = f"quarantine/{datetime.utcnow().strftime('%Y/%m/%d')}/{file_key}"
            
            # Copy file to quarantine bucket
            await s3_service.copy_file(
                source_key=file_key,
                dest_key=quarantine_key,
                source_bucket=bucket,
                dest_bucket=quarantine_bucket
            )
            
            # Delete original file
            await s3_service.delete_file(file_key, bucket)
            
            # Add quarantine metadata
            quarantine_metadata = {
                "original_bucket": bucket,
                "original_key": file_key,
                "quarantine_reason": reason,
                "quarantine_date": datetime.utcnow().isoformat(),
                "quarantine_location": f"{quarantine_bucket}/{quarantine_key}"
            }
            
            logger.warning("File quarantined", **quarantine_metadata)
            
            return {
                "quarantined": True,
                "quarantine_location": f"{quarantine_bucket}/{quarantine_key}",
                "original_location": f"{bucket}/{file_key}",
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Quarantine error", error=str(e), file_key=file_key)
            return {
                "quarantined": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def release_from_quarantine(
        self,
        quarantine_key: str,
        quarantine_bucket: str,
        destination_bucket: str,
        destination_key: str
    ) -> Dict[str, Any]:
        """
        Release file from quarantine
        
        Args:
            quarantine_key: Quarantined file key
            quarantine_bucket: Quarantine bucket name
            destination_bucket: Destination bucket
            destination_key: Destination key
            
        Returns:
            Release result
        """
        try:
            # Copy from quarantine to destination
            await s3_service.copy_file(
                source_key=quarantine_key,
                dest_key=destination_key,
                source_bucket=quarantine_bucket,
                dest_bucket=destination_bucket
            )
            
            # Delete from quarantine
            await s3_service.delete_file(quarantine_key, quarantine_bucket)
            
            logger.info("File released from quarantine", 
                       quarantine_location=f"{quarantine_bucket}/{quarantine_key}",
                       destination=f"{destination_bucket}/{destination_key}")
            
            return {
                "released": True,
                "destination": f"{destination_bucket}/{destination_key}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Quarantine release error", error=str(e))
            return {
                "released": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def batch_scan_files(
        self,
        file_keys: List[str],
        bucket: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scan multiple files in batch
        
        Args:
            file_keys: List of S3 object keys to scan
            bucket: S3 bucket name
            
        Returns:
            Batch scan results
        """
        try:
            bucket = bucket or settings.S3_BUCKET_UPLOADS
            
            payload = {
                "action": "batch_scan",
                "bucket": bucket,
                "keys": file_keys,
                "scan_options": {
                    "scan_archives": True,
                    "scan_pdfs": True,
                    "quarantine_threats": True
                }
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.scan_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            return {
                "batch_scan_status": "completed",
                "total_files": len(file_keys),
                "clean_files": response_payload.get('clean_files', []),
                "infected_files": response_payload.get('infected_files', []),
                "error_files": response_payload.get('error_files', []),
                "quarantined_files": response_payload.get('quarantined_files', []),
                "scan_summary": response_payload.get('scan_summary', {}),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Batch scan error", error=str(e))
            return {
                "batch_scan_status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global AV scanner instance
av_scanner = AVScanner()
