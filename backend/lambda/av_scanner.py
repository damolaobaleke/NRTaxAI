"""
AWS Lambda Function for Antivirus Scanning
"""

import json
import boto3
import hashlib
import tempfile
import os
import time
from typing import Dict, Any, Optional
import logging

# Configure logging first
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# VirusTotal integration
try:
    import vt
    VIRUSTOTAL_AVAILABLE = True
except ImportError:
    VIRUSTOTAL_AVAILABLE = False
    logger.warning("vt-py library not available. VirusTotal scanning will be disabled.")

# Initialize AWS clients
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

# Configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
QUARANTINE_BUCKET_SUFFIX = "-quarantine"

# VirusTotal configuration
VIRUSTOTAL_API_KEY = os.environ.get('VIRUSTOTAL_API_KEY')
VIRUSTOTAL_ENABLED = VIRUSTOTAL_AVAILABLE and VIRUSTOTAL_API_KEY is not None


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
    Perform antivirus scan on file content using VirusTotal API
    
    This function:
    1. Calculates file hash (SHA256)
    2. First tries hash lookup (faster, cheaper)
    3. Falls back to file upload scan if hash not found
    4. Returns detailed threat information
    
    Args:
        file_content: File content as bytes
        filename: Original filename
        scan_options: Scan configuration options
        
    Returns:
        Scan result dictionary with threat information
    """
    start_time = time.time()
    
    # Calculate file hash
    file_hash = hashlib.sha256(file_content).hexdigest()
    file_size = len(file_content)
    
    # Initialize result structure
    result = {
        'status': 'completed',
        'clean': True,
        'threats_detected': 0,
        'threats': [],
        'engine': 'VirusTotal',
        'version': '1.0.0',
        'duration_ms': 0,
        'file_hash': file_hash,
        'file_size_bytes': file_size,
        'filename': filename,
        'scan_options': scan_options,
        'scan_method': None,
        'vt_scan_id': None,
        'vt_scan_date': None
    }
    
    # If VirusTotal is not available, return error
    if not VIRUSTOTAL_ENABLED:
        logger.warning("VirusTotal not configured. Returning clean status.")
        result.update({
            'status': 'error',
            'engine': 'None',
            'error': 'VirusTotal API key not configured'
        })
        return result
    
    try:
        # Initialize VirusTotal client
        client = vt.Client(VIRUSTOTAL_API_KEY)
        
        # Strategy 1: Try hash lookup first (faster, no quota cost for public API)
        try:
            logger.info(f"Checking VirusTotal for hash: {file_hash[:16]}...")
            file_obj = client.get_object(f"/files/{file_hash}")
            
            # Get scan results
            last_analysis = file_obj.last_analysis_stats
            result['vt_scan_date'] = file_obj.last_analysis_date.isoformat() if file_obj.last_analysis_date else None
            result['scan_method'] = 'hash_lookup'
            
            # Check if file is malicious
            malicious_count = last_analysis.get('malicious', 0)
            suspicious_count = last_analysis.get('suspicious', 0)
            
            if malicious_count > 0 or suspicious_count > 0:
                result['clean'] = False
                result['threats_detected'] = malicious_count + suspicious_count
                
                # Get detailed threat information
                threats = []
                for engine, analysis in file_obj.last_analysis_results.items():
                    if analysis.get('category') in ['malicious', 'suspicious']:
                        threats.append({
                            'engine': engine,
                            'category': analysis.get('category', 'unknown'),
                            'result': analysis.get('result', 'Threat detected'),
                            'method': analysis.get('method', 'signature')
                        })
                
                result['threats'] = threats[:10]  # Limit to top 10 threats
                
                logger.warning(f"Threat detected in {filename}: {result['threats_detected']} engines flagged it")
            
            else:
                logger.info(f"File {filename} is clean according to VirusTotal")
            
            client.close()
            
        except vt.APIError as e:
            # Hash not found, need to upload file for scanning
            if e.code == 'NotFoundError':
                logger.info(f"Hash not found in VirusTotal, uploading file for scanning: {filename}")
                result['scan_method'] = 'file_upload'
                
                # Upload file for scanning
                # Note: VirusTotal has file size limits (32MB for free tier, 200MB for paid)
                max_upload_size = 32 * 1024 * 1024  # 32MB default limit
                if file_size > max_upload_size:
                    logger.warning(f"File too large for VirusTotal upload: {file_size} bytes")
                    result.update({
                        'status': 'error',
                        'error': f'File too large for upload (max {max_upload_size} bytes)',
                        'clean': True  # Assume clean if we can't scan
                    })
                    client.close()
                    return result
                
                # Upload file
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    tmp_file.write(file_content)
                    tmp_file.flush()
                    
                    try:
                        # Upload to VirusTotal
                        with open(tmp_file.name, 'rb') as f:
                            analysis = client.scan_file(f, wait_for_completion=False)
                        
                        scan_id = analysis.id
                        result['vt_scan_id'] = scan_id
                        
                        # Wait for scan to complete (with timeout)
                        max_wait_time = 300  # 5 minutes
                        wait_start = time.time()
                        poll_interval = 5  # Check every 5 seconds
                        
                        while time.time() - wait_start < max_wait_time:
                            analysis = client.get_object(f"/analyses/{scan_id}")
                            
                            if analysis.status == 'completed':
                                # Get file object for results
                                file_obj = client.get_object(f"/files/{file_hash}")
                                last_analysis = file_obj.last_analysis_stats
                                
                                malicious_count = last_analysis.get('malicious', 0)
                                suspicious_count = last_analysis.get('suspicious', 0)
                                
                                if malicious_count > 0 or suspicious_count > 0:
                                    result['clean'] = False
                                    result['threats_detected'] = malicious_count + suspicious_count
                                    
                                    # Get detailed threats
                                    threats = []
                                    for engine, analysis_result in file_obj.last_analysis_results.items():
                                        if analysis_result.get('category') in ['malicious', 'suspicious']:
                                            threats.append({
                                                'engine': engine,
                                                'category': analysis_result.get('category', 'unknown'),
                                                'result': analysis_result.get('result', 'Threat detected'),
                                                'method': analysis_result.get('method', 'signature')
                                            })
                                    
                                    result['threats'] = threats[:10]
                                    logger.warning(f"Threat detected after upload scan: {result['threats_detected']} engines")
                                else:
                                    logger.info(f"File is clean after upload scan")
                                
                                result['vt_scan_date'] = file_obj.last_analysis_date.isoformat() if file_obj.last_analysis_date else None
                                break
                            
                            elif analysis.status == 'error':
                                raise Exception(f"VirusTotal scan error: {analysis.status}")
                            
                            time.sleep(poll_interval)
                        else:
                            # Timeout - return pending status
                            result.update({
                                'status': 'pending',
                                'error': 'Scan timeout - results may be available later',
                                'clean': True  # Assume clean until confirmed malicious
                            })
                        
                        os.unlink(tmp_file.name)
                        
                    except Exception as upload_error:
                        os.unlink(tmp_file.name)
                        raise upload_error
                
                client.close()
                
            else:
                # Other API error
                logger.error(f"VirusTotal API error: {str(e)}")
                result.update({
                    'status': 'error',
                    'error': f'VirusTotal API error: {str(e)}',
                    'clean': True  # Assume clean on error
                })
                client.close()
        
        except Exception as e:
            logger.error(f"VirusTotal scan error: {str(e)}", exc_info=True)
            result.update({
                'status': 'error',
                'error': str(e),
                'clean': True  # Default to clean on error
            })
            try:
                client.close()
            except:
                pass
    
    except Exception as e:
        logger.error(f"Unexpected error during AV scan: {str(e)}", exc_info=True)
        result.update({
            'status': 'error',
            'error': str(e),
            'clean': True
        })
    
    finally:
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        result['duration_ms'] = duration_ms
    
    return result


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
