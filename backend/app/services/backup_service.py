"""
Backup Service for Database and Files
"""

import boto3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class BackupService:
    """Service for automated backups"""
    
    def __init__(self):
        self.rds_client = boto3.client(
            'rds',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.s3_client = boto3.client('s3')
        self.backup_bucket = "nrtaxai-backups"
    
    async def create_database_snapshot(
        self,
        db_instance_id: str = "nrtaxai-postgres"
    ) -> Dict[str, Any]:
        """
        Create RDS database snapshot
        
        Args:
            db_instance_id: RDS instance identifier
            
        Returns:
            Snapshot metadata
        """
        try:
            snapshot_id = f"nrtaxai-snapshot-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            
            logger.info("Creating database snapshot", 
                       db_instance_id=db_instance_id,
                       snapshot_id=snapshot_id)
            
            response = self.rds_client.create_db_snapshot(
                DBSnapshotIdentifier=snapshot_id,
                DBInstanceIdentifier=db_instance_id,
                Tags=[
                    {'Key': 'Environment', 'Value': settings.ENVIRONMENT},
                    {'Key': 'BackupType', 'Value': 'manual'},
                    {'Key': 'CreatedAt', 'Value': datetime.utcnow().isoformat()}
                ]
            )
            
            snapshot = response['DBSnapshot']
            
            logger.info("Database snapshot created", 
                       snapshot_id=snapshot_id,
                       status=snapshot['Status'])
            
            return {
                "snapshot_id": snapshot_id,
                "status": snapshot['Status'],
                "db_instance_id": db_instance_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Database snapshot creation failed", error=str(e))
            raise Exception(f"Failed to create snapshot: {str(e)}")
    
    async def list_database_snapshots(
        self,
        db_instance_id: str = "nrtaxai-postgres",
        max_records: int = 20
    ) -> List[Dict[str, Any]]:
        """List database snapshots"""
        try:
            response = self.rds_client.describe_db_snapshots(
                DBInstanceIdentifier=db_instance_id,
                MaxRecords=max_records
            )
            
            snapshots = []
            for snapshot in response.get('DBSnapshots', []):
                snapshots.append({
                    "snapshot_id": snapshot['DBSnapshotIdentifier'],
                    "status": snapshot['Status'],
                    "created_at": snapshot.get('SnapshotCreateTime').isoformat() if snapshot.get('SnapshotCreateTime') else None,
                    "size_gb": snapshot.get('AllocatedStorage', 0)
                })
            
            return snapshots
            
        except Exception as e:
            logger.error("Failed to list snapshots", error=str(e))
            raise Exception(f"Failed to list snapshots: {str(e)}")
    
    async def restore_database_snapshot(
        self,
        snapshot_id: str,
        new_instance_id: str
    ) -> Dict[str, Any]:
        """Restore database from snapshot"""
        try:
            logger.info("Restoring database from snapshot", 
                       snapshot_id=snapshot_id,
                       new_instance_id=new_instance_id)
            
            response = self.rds_client.restore_db_instance_from_db_snapshot(
                DBInstanceIdentifier=new_instance_id,
                DBSnapshotIdentifier=snapshot_id,
                DBInstanceClass='db.t3.medium',
                PubliclyAccessible=False,
                Tags=[
                    {'Key': 'RestoredFrom', 'Value': snapshot_id},
                    {'Key': 'RestoredAt', 'Value': datetime.utcnow().isoformat()}
                ]
            )
            
            return {
                "instance_id": new_instance_id,
                "snapshot_id": snapshot_id,
                "status": response['DBInstance']['DBInstanceStatus'],
                "restored_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Database restore failed", error=str(e))
            raise Exception(f"Failed to restore database: {str(e)}")
    
    async def cleanup_old_snapshots(
        self,
        retention_days: int = 30,
        db_instance_id: str = "nrtaxai-postgres"
    ) -> Dict[str, Any]:
        """Delete snapshots older than retention period"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            snapshots = await self.list_database_snapshots(db_instance_id)
            
            deleted_count = 0
            for snapshot in snapshots:
                snapshot_date = datetime.fromisoformat(snapshot['created_at'])
                
                if snapshot_date < cutoff_date:
                    try:
                        self.rds_client.delete_db_snapshot(
                            DBSnapshotIdentifier=snapshot['snapshot_id']
                        )
                        deleted_count += 1
                        logger.info("Deleted old snapshot", 
                                   snapshot_id=snapshot['snapshot_id'])
                    except Exception as e:
                        logger.warning("Failed to delete snapshot", 
                                      snapshot_id=snapshot['snapshot_id'],
                                      error=str(e))
            
            return {
                "deleted_count": deleted_count,
                "retention_days": retention_days,
                "cleanup_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Snapshot cleanup failed", error=str(e))
            raise Exception(f"Failed to cleanup snapshots: {str(e)}")
    
    async def backup_s3_to_glacier(
        self,
        source_bucket: str,
        retention_days: int = 90
    ) -> Dict[str, Any]:
        """
        Configure S3 lifecycle policy to move old files to Glacier
        
        Args:
            source_bucket: S3 bucket name
            retention_days: Days before moving to Glacier
            
        Returns:
            Configuration result
        """
        try:
            lifecycle_config = {
                'Rules': [
                    {
                        'Id': 'ArchiveOldDocuments',
                        'Status': 'Enabled',
                        'Prefix': '',
                        'Transitions': [
                            {
                                'Days': retention_days,
                                'StorageClass': 'GLACIER'
                            }
                        ],
                        'NoncurrentVersionTransitions': [
                            {
                                'NoncurrentDays': 30,
                                'StorageClass': 'GLACIER'
                            }
                        ]
                    }
                ]
            }
            
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=source_bucket,
                LifecycleConfiguration=lifecycle_config
            )
            
            logger.info("S3 lifecycle policy configured", 
                       bucket=source_bucket,
                       retention_days=retention_days)
            
            return {
                "bucket": source_bucket,
                "retention_days": retention_days,
                "storage_class": "GLACIER",
                "configured_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("S3 lifecycle configuration failed", error=str(e))
            raise Exception(f"Failed to configure S3 lifecycle: {str(e)}")


# Global backup service instance
backup_service = BackupService()
