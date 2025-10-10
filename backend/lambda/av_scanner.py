"""
AWS Lambda Function for Antivirus Scanning
"""

import json
import boto3
import hashlib
import tempfile
import os
from typing import Dict, Any
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

# Configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
QUARANTINE_BUCKET_SUFFIX = "-quarantine"


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for antivirus scanning
    
    Args:
        event: Lambda event containing scan parameters
        context: Lambda context
        
    Returns:
        Scan result dictionary
    """
    try:
        logger.info(f"AV scan request: {json.dumps(event)}")
        
        action = event.get('action', 'scan')
        
        if action == 'scan':
            return handle_single_scan(event)
        elif action == 'batch_scan':
            return handle_batch_scan(event)
        elif action == 'status':
            return handle_scan_status(event)
        else:
            return {
                'error': f'Unknown action: {action}',
                'statusCode': 400
            }
            
    except Exception as e:
        logger.error(f"Lambda error: {str(e)}", exc_info=True)
        return {
            'error': str(e),
            'statusCode': 500
        }


def handle_single_scan(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle single file scan"""
    try:
        bucket = event.get('bucket')
        key = event.get('key')
        scan_type = event.get('scan_type', 'full')
        scan_options = event.get('scan_options', {})
        
        if not bucket or not key:
            raise ValueError("Missing bucket or key parameters")
        
        # Download file from S3
        file_content = download_file_from_s3(bucket, key)
        
        if not file_content:
            raise ValueError("Failed to download file from S3")
        
        # Check file size
        if len(file_content) > MAX_FILE_SIZE:
            return {
                'scan_result': {
                    'status': 'skipped',
                    'reason': 'file_too_large',
                    'file_size_bytes': len(file_content),
                    'max_scan_size': MAX_FILE_SIZE
                }
            }
        
        # Perform antivirus scan
        scan_result = perform_av_scan(file_content, key, scan_options)
        
        # If threats detected, quarantine file
        if scan_result.get('threats_detected', 0) > 0:
            quarantine_result = quarantine_file(bucket, key, scan_result)
            scan_result['quarantined'] = quarantine_result.get('quarantined', False)
            scan_result['quarantine_location'] = quarantine_result.get('quarantine_location', '')
        
        return {
            'scan_result': scan_result
        }
        
    except Exception as e:
        logger.error(f"Single scan error: {str(e)}")
        return {
            'error': str(e),
            'scan_result': {
                'status': 'error',
                'error_message': str(e)
            }
        }


def handle_batch_scan(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle batch file scanning"""
    try:
        bucket = event.get('bucket')
        keys = event.get('keys', [])
        scan_options = event.get('scan_options', {})
        
        if not bucket or not keys:
            raise ValueError("Missing bucket or keys parameters")
        
        clean_files = []
        infected_files = []
        error_files = []
        quarantined_files = []
        
        for key in keys:
            try:
                # Download and scan file
                file_content = download_file_from_s3(bucket, key)
                
                if not file_content:
                    error_files.append({
                        'key': key,
                        'error': 'Failed to download file'
                    })
                    continue
                
                # Check file size
                if len(file_content) > MAX_FILE_SIZE:
                    error_files.append({
                        'key': key,
                        'error': 'File too large for scanning',
                        'size_bytes': len(file_content)
                    })
                    continue
                
                # Perform scan
                scan_result = perform_av_scan(file_content, key, scan_options)
                
                if scan_result.get('threats_detected', 0) > 0:
                    infected_files.append({
                        'key': key,
                        'threats': scan_result.get('threats', []),
                        'scan_result': scan_result
                    })
                    
                    # Quarantine if configured
                    if scan_options.get('quarantine_threats', False):
                        quarantine_result = quarantine_file(bucket, key, scan_result)
                        if quarantine_result.get('quarantined', False):
                            quarantined_files.append({
                                'key': key,
                                'quarantine_location': quarantine_result.get('quarantine_location', ''),
                                'scan_result': scan_result
                            })
                else:
                    clean_files.append({
                        'key': key,
                        'scan_result': scan_result
                    })
                    
            except Exception as e:
                logger.error(f"Batch scan error for {key}: {str(e)}")
                error_files.append({
                    'key': key,
                    'error': str(e)
                })
        
        # Generate summary
        scan_summary = {
            'total_files': len(keys),
            'clean_files': len(clean_files),
            'infected_files': len(infected_files),
            'error_files': len(error_files),
            'quarantined_files': len(quarantined_files)
        }
        
        return {
            'clean_files': clean_files,
            'infected_files': infected_files,
            'error_files': error_files,
            'quarantined_files': quarantined_files,
            'scan_summary': scan_summary
        }
        
    except Exception as e:
        logger.error(f"Batch scan error: {str(e)}")
        return {
            'error': str(e),
            'batch_scan_status': 'error'
        }


def handle_scan_status(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle scan status request"""
    try:
        scan_id = event.get('scan_id')
        
        # This would typically check a DynamoDB table or SQS queue
        # For now, return a placeholder response
        return {
            'status_result': {
                'scan_id': scan_id,
                'status': 'completed',
                'message': 'Scan status checking not implemented'
            }
        }
        
    except Exception as e:
        logger.error(f"Scan status error: {str(e)}")
        return {
            'error': str(e),
            'status_result': {
                'status': 'error',
                'error_message': str(e)
            }
        }


def download_file_from_s3(bucket: str, key: str) -> bytes:
    """Download file from S3"""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        logger.error(f"S3 download error for {bucket}/{key}: {str(e)}")
        return None


def perform_av_scan(file_content: bytes, filename: str, scan_options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform antivirus scan on file content
    
    Note: This is a placeholder implementation. In production, you would:
    1. Use a real antivirus engine (ClamAV, Windows Defender, etc.)
    2. Scan for malware, trojans, viruses, etc.
    3. Return detailed threat information
    
    Args:
        file_content: File content as bytes
        filename: Original filename
        scan_options: Scan configuration options
        
    Returns:
        Scan result dictionary
    """
    import time
    import random
    
    # Simulate scan duration
    scan_duration = random.randint(100, 2000)  # 100ms to 2s
    time.sleep(scan_duration / 1000.0)
    
    # Calculate file hash
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # Simulate threat detection (5% chance for demo)
    threats_detected = 0
    threats = []
    
    if random.random() < 0.05:  # 5% chance of "infection"
        threats_detected = random.randint(1, 3)
        threat_types = ["Trojan.Generic", "Malware.Heuristic", "Virus.Generic"]
        
        for i in range(threats_detected):
            threats.append({
                'type': random.choice(threat_types),
                'severity': random.choice(['High', 'Medium', 'Low']),
                'description': f'Detected threat pattern {i+1}',
                'signature': f'SIG-{random.randint(1000, 9999)}'
            })
    
    return {
        'status': 'completed',
        'clean': threats_detected == 0,
        'threats_detected': threats_detected,
        'threats': threats,
        'engine': 'NRTaxAI-AV-Engine',
        'version': '1.0.0',
        'duration_ms': scan_duration,
        'file_hash': file_hash,
        'file_size_bytes': len(file_content),
        'filename': filename,
        'scan_options': scan_options
    }


def quarantine_file(bucket: str, key: str, scan_result: Dict[str, Any]) -> Dict[str, Any]:
    """Quarantine infected file"""
    try:
        quarantine_bucket = f"{bucket}{QUARANTINE_BUCKET_SUFFIX}"
        quarantine_key = f"quarantine/{key}"
        
        # Copy file to quarantine bucket
        copy_source = {'Bucket': bucket, 'Key': key}
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=quarantine_bucket,
            Key=quarantine_key,
            Metadata={
                'original_bucket': bucket,
                'original_key': key,
                'quarantine_reason': 'malware_detected',
                'threats_detected': str(scan_result.get('threats_detected', 0)),
                'scan_timestamp': str(int(time.time()))
            }
        )
        
        # Delete original file
        s3_client.delete_object(Bucket=bucket, Key=key)
        
        logger.warning(f"File quarantined: {bucket}/{key} -> {quarantine_bucket}/{quarantine_key}")
        
        return {
            'quarantined': True,
            'quarantine_location': f"{quarantine_bucket}/{quarantine_key}",
            'original_location': f"{bucket}/{key}"
        }
        
    except Exception as e:
        logger.error(f"Quarantine error for {bucket}/{key}: {str(e)}")
        return {
            'quarantined': False,
            'error': str(e)
        }


# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        "action": "scan",
        "bucket": "test-bucket",
        "key": "test-file.pdf",
        "scan_type": "full",
        "scan_options": {
            "scan_archives": True,
            "scan_pdfs": True,
            "quarantine_threats": True
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
