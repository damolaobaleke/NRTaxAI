"""
Deploy AV Scanner Lambda Function
"""

import boto3
import zipfile
import os
import tempfile
import json
from typing import Dict, Any

def create_lambda_package() -> bytes:
    """Create Lambda deployment package and return zip file contents as bytes"""
    import subprocess
    import sys
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        package_path = os.path.join(temp_dir, "av_scanner.zip")
        
        # Install dependencies to a temporary directory
        lambda_dir = os.path.join(os.path.dirname(__file__), 'lambda')
        requirements_file = os.path.join(lambda_dir, 'requirements.txt')
        
        if os.path.exists(requirements_file):
            # Install dependencies to temp_dir
            install_dir = os.path.join(temp_dir, 'python')
            os.makedirs(install_dir, exist_ok=True)
            
            print(f"Installing dependencies from {requirements_file}...")
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install',
                '-r', requirements_file,
                '-t', install_dir,
                '--no-cache-dir',
                '--upgrade'
            ])
        
        # Create zip file
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add main Lambda function
            lambda_file = os.path.join(lambda_dir, 'av_scanner.py')
            if not os.path.exists(lambda_file):
                raise FileNotFoundError(f"Lambda function file not found: {lambda_file}")
            zip_file.write(lambda_file, 'av_scanner.py')
            
            # Add installed dependencies
            if os.path.exists(install_dir):
                for root, dirs, files in os.walk(install_dir):
                    # Skip __pycache__ and .pyc files
                    dirs[:] = [d for d in dirs if d != '__pycache__']
                    for file in files:
                        if not file.endswith('.pyc'):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, install_dir)
                            zip_file.write(file_path, arcname)
        
        # Read the zip file contents before the temp directory is deleted
        with open(package_path, 'rb') as f:
            zip_contents = f.read()
        
        return zip_contents

def deploy_lambda_function(
    function_name: str = "nrtaxai-av-scanner",
    region: str = "us-east-1",
    role_arn: str = None
) -> Dict[str, Any]:
    """Deploy or update Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Create deployment package (returns bytes)
    zip_contents = create_lambda_package()
    
    try:
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=function_name)
            function_exists = True
        except lambda_client.exceptions.ResourceNotFoundException:
            function_exists = False
        
        if function_exists:
            # Update existing function
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_contents
            )
            
            print(f"✅ Updated Lambda function: {function_name}")
            
        else:
            # Create new function
            if not role_arn:
                raise ValueError("role_arn is required for new function creation")
            
            # Get VirusTotal API key from environment if available
            env_vars = {
                'LOG_LEVEL': 'INFO'
            }
            virustotal_key = os.environ.get('VIRUSTOTAL_API_KEY')
            if virustotal_key:
                env_vars['VIRUSTOTAL_API_KEY'] = virustotal_key
                print("✅ VirusTotal API key configured from environment")
            else:
                print("⚠️  Warning: VIRUSTOTAL_API_KEY not set. Set it in Lambda environment variables after deployment.")
            
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='av_scanner.lambda_handler',
                Code={'ZipFile': zip_contents},
                Description='NRTaxAI Antivirus Scanner',
                Timeout=300,  # 5 minutes
                MemorySize=1024,  # 1GB
                Environment={
                    'Variables': env_vars
                }
            )
            
            print(f"✅ Created Lambda function: {function_name}")
        
        return {
            "success": True,
            "function_name": function_name,
            "function_arn": response['FunctionArn'],
            "last_modified": response['LastModified']
        }
        
    except Exception as e:
        print(f"❌ Lambda deployment failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def create_lambda_role(region: str = "us-east-1") -> str:
    """Create IAM role for Lambda function"""
    
    iam_client = boto3.client('iam', region_name=region)
    
    role_name = "NRTaxAI-AVScanner-Role"
    
    # Trust policy for Lambda
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Permissions policy
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:CopyObject"
                ],
                "Resource": [
                    "arn:aws:s3:::nrtaxai-uploads/*",
                    "arn:aws:s3:::nrtaxai-uploads-quarantine/*",
                    "arn:aws:s3:::nrtaxai-pdfs/*",
                    "arn:aws:s3:::nrtaxai-extracts/*"
                ]
            }
        ]
    }
    
    try:
        # Create role
        try:
            iam_client.get_role(RoleName=role_name)
            print(f"✅ IAM role already exists: {role_name}")
        except iam_client.exceptions.NoSuchEntityException:
            iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Role for NRTaxAI AV Scanner Lambda function"
            )
            print(f"✅ Created IAM role: {role_name}")
        
        # Attach permissions policy
        policy_name = f"{role_name}-Policy"
        try:
            iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            print(f"✅ Policy already attached: {policy_name}")
        except iam_client.exceptions.NoSuchEntityException:
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(permissions_policy)
            )
            print(f"✅ Attached policy: {policy_name}")
        
        # Get role ARN
        role_response = iam_client.get_role(RoleName=role_name)
        role_arn = role_response['Role']['Arn']
        
        return role_arn
        
    except Exception as e:
        print(f"❌ IAM role creation failed: {str(e)}")
        raise

def main():
    """Main deployment function"""
    print("🚀 Deploying NRTaxAI AV Scanner Lambda Function")
    print("=" * 50)
    
    region = "us-east-1"
    
    try:
        # Create IAM role
        print("Creating IAM role...")
        role_arn = create_lambda_role(region)
        
        # Deploy Lambda function
        print("Deploying Lambda function...")
        result = deploy_lambda_function(
            function_name="nrtaxai-av-scanner",
            region=region,
            role_arn=role_arn
        )
        
        if result["success"]:
            print("\n🎉 Deployment successful!")
            print(f"Function ARN: {result['function_arn']}")
            print(f"Last Modified: {result['last_modified']}")
        else:
            print(f"\n❌ Deployment failed: {result['error']}")
            
    except Exception as e:
        print(f"\n❌ Deployment error: {str(e)}")

if __name__ == "__main__":
    main()
