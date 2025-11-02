"""
AWS S3 Service for Document Storage
"""

import boto3
import hashlib
import mimetypes
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from botocore.exceptions import ClientError, NoCredentialsError
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class S3Service:
    """S3 service for document storage and management"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.upload_bucket = settings.S3_BUCKET_UPLOADS
        self.pdf_bucket = settings.S3_BUCKET_PDFS
        self.extract_bucket = settings.S3_BUCKET_EXTRACTS
    
    async def generate_presigned_upload_url(
        self,
        user_id: str,
        document_type: str,
        file_extension: str,
        expires_in: int = 3600
    ) -> Dict[str, Any]:
        """
        Generate pre-signed URL for secure document upload
        
        Args:
            user_id: User ID for folder organization
            document_type: Type of document (W2, 1099INT, etc.)
            file_extension: File extension (pdf, png, jpg, jpeg)
            expires_in: URL expiration time in seconds
            
        Returns:
            Dict with upload URL and metadata
        """
        try:
            # Generate unique file key
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            #
            file_key = f"uploads/{user_id}/{document_type}_{timestamp}.{file_extension}"
            
            # Determine content type
            content_type = mimetypes.guess_type(f"file.{file_extension}")[0]
            if not content_type:
                content_type = "application/octet-stream"
            
            # Generate pre-signed POST data
            conditions = [
                {"bucket": self.upload_bucket},
                ["starts-with", "$key", f"uploads/{user_id}/"],
                {"Content-Type": content_type},
                ["content-length-range", 1, settings.MAX_FILE_SIZE]
            ]
            
            # Add file type restrictions
            if file_extension.lower() in settings.ALLOWED_FILE_TYPES:
                conditions.append(["starts-with", "$key", f"uploads/{user_id}/{document_type}_"])
            
            post_data = self.s3_client.generate_presigned_post(
                Bucket=self.upload_bucket,
                Key=file_key,
                Fields={"Content-Type": content_type},
                Conditions=conditions,
                ExpiresIn=expires_in
            )

            logger.info("Generated presigned POST data", post_data)
            
            return {
                "upload_url": post_data["url"],
                "fields": post_data["fields"],
                "file_key": file_key,
                "content_type": content_type,
                "expires_at": datetime.now() + timedelta(seconds=expires_in)
            }
            
        except NoCredentialsError:
            logger.error("AWS credentials not configured")
            raise Exception("AWS credentials not configured")
        except ClientError as e:
            logger.error("S3 error generating presigned URL", error=str(e))
            raise Exception(f"Failed to generate upload URL: {str(e)}")
    
    async def upload_file(
        self,
        file_key: str,
        file_content: bytes,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload file directly to S3
        
        Args:
            file_key: S3 object key
            file_content: File content as bytes
            bucket: Bucket name (defaults to upload bucket)
            metadata: Additional metadata
            
        Returns:
            Upload result with metadata
        """
        try:
            bucket = bucket or self.upload_bucket
            
            # Calculate file hash
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Prepare upload parameters
            upload_params = {
                'Bucket': bucket,
                'Key': file_key,
                'Body': file_content,
                'Metadata': {
                    'uploaded_at': datetime.now().isoformat(),
                    'file_hash': file_hash,
                    **(metadata or {})
                }
            }
            
            # Upload file
            response = self.s3_client.put_object(**upload_params)
            
            return {
                "success": True,
                "bucket": bucket,
                "key": file_key,
                "etag": response.get('ETag', '').strip('"'),
                "file_hash": file_hash,
                "size_bytes": len(file_content),
                "upload_time": datetime.now()
            }
            
        except ClientError as e:
            logger.error("S3 upload error", error=str(e), file_key=file_key)
            raise Exception(f"Failed to upload file: {str(e)}")
    
    async def download_file(self, file_key: str, bucket: Optional[str] = None) -> bytes:
        """
        Download file from S3
        
        Args:
            file_key: S3 object key
            bucket: Bucket name (defaults to upload bucket)
            
        Returns:
            File content as bytes
        """
        try:
            bucket = bucket or self.upload_bucket
            
            response = self.s3_client.get_object(Bucket=bucket, Key=file_key)
            return response['Body'].read()
            
        except ClientError as e:
            logger.error("S3 download error", error=str(e), file_key=file_key)
            raise Exception(f"Failed to download file: {str(e)}")
    
    async def delete_file(self, file_key: str, bucket: Optional[str] = None) -> bool:
        """
        Delete file from S3
        
        Args:
            file_key: S3 object key
            bucket: Bucket name (defaults to upload bucket)
            
        Returns:
            Success status
        """
        try:
            bucket = bucket or self.upload_bucket
            
            self.s3_client.delete_object(Bucket=bucket, Key=file_key)
            return True
            
        except ClientError as e:
            logger.error("S3 delete error", error=str(e), file_key=file_key)
            return False
    
    async def get_file_metadata(self, file_key: str, bucket: Optional[str] = None) -> Dict[str, Any]:
        """
        Get file metadata from S3
        
        Args:
            file_key: S3 object key
            bucket: Bucket name (defaults to upload bucket)
            
        Returns:
            File metadata
        """
        try:
            bucket = bucket or self.upload_bucket
            
            response = self.s3_client.head_object(Bucket=bucket, Key=file_key)
            
            return {
                "size_bytes": response.get('ContentLength', 0),
                "content_type": response.get('ContentType', ''),
                "last_modified": response.get('LastModified'),
                "etag": response.get('ETag', '').strip('"'),
                "metadata": response.get('Metadata', {}),
                "file_key": file_key,
                "bucket": bucket
            }
            
        except ClientError as e:
            logger.error("S3 metadata error", error=str(e), file_key=file_key)
            raise Exception(f"Failed to get file metadata: {str(e)}")
    
    async def copy_file(
        self,
        source_key: str,
        dest_key: str,
        source_bucket: Optional[str] = None,
        dest_bucket: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Copy file within S3
        
        Args:
            source_key: Source S3 object key
            dest_key: Destination S3 object key
            source_bucket: Source bucket name
            dest_bucket: Destination bucket name
            
        Returns:
            Copy result
        """
        try:
            source_bucket = source_bucket or self.upload_bucket
            dest_bucket = dest_bucket or self.upload_bucket
            
            copy_source = {'Bucket': source_bucket, 'Key': source_key}
            
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=dest_key
            )
            
            return {
                "success": True,
                "source": f"{source_bucket}/{source_key}",
                "destination": f"{dest_bucket}/{dest_key}"
            }
            
        except ClientError as e:
            logger.error("S3 copy error", error=str(e))
            raise Exception(f"Failed to copy file: {str(e)}")
    
    async def list_files(
        self,
        prefix: str,
        bucket: Optional[str] = None,
        max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List files in S3 bucket with prefix
        
        Args:
            prefix: Key prefix to filter
            bucket: Bucket name (defaults to upload bucket)
            max_keys: Maximum number of keys to return
            
        Returns:
            List of file metadata
        """
        try:
            bucket = bucket or self.upload_bucket
            
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "key": obj['Key'],
                    "size_bytes": obj['Size'],
                    "last_modified": obj['LastModified'],
                    "etag": obj['ETag'].strip('"')
                })
            
            return files
            
        except ClientError as e:
            logger.error("S3 list error", error=str(e))
            raise Exception(f"Failed to list files: {str(e)}")
    
    async def generate_presigned_download_url(
        self,
        file_key: str,
        bucket: Optional[str] = None,
        expires_in: int = 3600
    ) -> str:
        """
        Generate pre-signed URL for secure file download
        
        Args:
            file_key: S3 object key
            bucket: Bucket name (defaults to upload bucket)
            expires_in: URL expiration time in seconds
            
        Returns:
            Pre-signed download URL
        """
        try:
            bucket = bucket or self.upload_bucket
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': file_key},
                ExpiresIn=expires_in
            )
            
            return url
            
        except ClientError as e:
            logger.error("S3 presigned URL error", error=str(e))
            raise Exception(f"Failed to generate download URL: {str(e)}")


# Global S3 service instance
s3_service = S3Service()
