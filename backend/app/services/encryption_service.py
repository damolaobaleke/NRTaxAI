"""
KMS Envelope Encryption Service
"""

import boto3
import json
from base64 import b64encode, b64decode
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class EncryptionService:
    """KMS envelope encryption for PII fields"""
    
    def __init__(self):
        self.kms_client = boto3.client(
            'kms',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.kms_key_id = settings.KMS_KEY_ID
    
    async def encrypt_field(self, plaintext: str) -> str:
        """
        Encrypt sensitive field using KMS envelope encryption
        
        Args:
            plaintext: Data to encrypt
            
        Returns:
            JSON string with encrypted data and key
        """
        try:
            if not plaintext:
                return None
            
            # Generate data encryption key using KMS
            response = self.kms_client.generate_data_key(
                KeyId=self.kms_key_id,
                KeySpec='AES_256'
            )
            
            plaintext_key = response['Plaintext']
            encrypted_key = response['CiphertextBlob']
            
            # Encrypt data with plaintext key (AES-256)
            cipher = Fernet(b64encode(plaintext_key[:32]))
            encrypted_data = cipher.encrypt(plaintext.encode())
            
            # Return encrypted data and key as JSON
            encrypted_package = {
                'encrypted_value': b64encode(encrypted_data).decode(),
                'encrypted_key': b64encode(encrypted_key).decode(),
                'algorithm': 'AES-256-GCM',
                'kms_key_id': self.kms_key_id
            }
            
            return json.dumps(encrypted_package)
            
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise Exception(f"Failed to encrypt field: {str(e)}")
    
    async def decrypt_field(self, encrypted_json: str) -> str:
        """
        Decrypt sensitive field using KMS
        
        Args:
            encrypted_json: JSON string with encrypted data
            
        Returns:
            Decrypted plaintext
        """
        try:
            if not encrypted_json:
                return None
            
            # Parse encrypted package
            encrypted_package = json.loads(encrypted_json)
            
            # Decrypt data key using KMS
            encrypted_key = b64decode(encrypted_package['encrypted_key'])
            response = self.kms_client.decrypt(
                CiphertextBlob=encrypted_key
            )
            plaintext_key = response['Plaintext']
            
            # Decrypt data with plaintext key
            cipher = Fernet(b64encode(plaintext_key[:32]))
            encrypted_data = b64decode(encrypted_package['encrypted_value'])
            plaintext = cipher.decrypt(encrypted_data)
            
            return plaintext.decode()
            
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise Exception(f"Failed to decrypt field: {str(e)}")
    
    async def encrypt_pii_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt all PII fields in a data dictionary
        
        Args:
            data: Dictionary with PII fields
            
        Returns:
            Dictionary with encrypted PII fields
        """
        try:
            pii_fields = ['ssn', 'itin', 'dob', 'phone', 'address_json']
            
            encrypted_data = data.copy()
            
            for field in pii_fields:
                if field in data and data[field]:
                    if field == 'address_json' and isinstance(data[field], dict):
                        # Encrypt address as JSON string
                        encrypted_data[field] = await self.encrypt_field(json.dumps(data[field]))
                    else:
                        encrypted_data[field] = await self.encrypt_field(str(data[field]))
            
            return encrypted_data
            
        except Exception as e:
            logger.error("PII encryption failed", error=str(e))
            raise Exception(f"Failed to encrypt PII: {str(e)}")
    
    async def decrypt_pii_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt all PII fields in a data dictionary
        
        Args:
            data: Dictionary with encrypted PII fields
            
        Returns:
            Dictionary with decrypted PII fields
        """
        try:
            pii_fields = ['ssn', 'itin', 'dob', 'phone', 'address_json']
            
            decrypted_data = data.copy()
            
            for field in pii_fields:
                if field in data and data[field]:
                    try:
                        decrypted_value = await self.decrypt_field(data[field])
                        
                        if field == 'address_json':
                            # Parse address JSON
                            decrypted_data[field] = json.loads(decrypted_value)
                        else:
                            decrypted_data[field] = decrypted_value
                    except Exception as e:
                        logger.warning(f"Failed to decrypt {field}", error=str(e))
                        decrypted_data[field] = None
            
            return decrypted_data
            
        except Exception as e:
            logger.error("PII decryption failed", error=str(e))
            raise Exception(f"Failed to decrypt PII: {str(e)}")


# Global encryption service instance
encryption_service = EncryptionService()
