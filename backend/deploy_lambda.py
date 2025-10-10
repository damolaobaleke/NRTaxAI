"""
Deploy AV Scanner Lambda Function
"""

import boto3
import zipfile
import os
import tempfile
import json
from typing import Dict, Any

def create_lambda_package() -> str:
    """Create Lambda deployment package"""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        package_path = os.path.join(temp_dir, "av_scanner.zip")
        
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add main Lambda function
            lambda_file = os.path.join(os.path.dirname(__file__), 'lambda', 'av_scanner.py')
            zip_file.write(lambda_file, 'av_scanner.py')
            
            # Add requirements (install them first)
            requirements_file = os.path.join(os.path.dirname(__file__), 'lambda', 'requirements.txt')
            if os.path.exists(requirements_file):
                zip_file.write(requirements_file, 'requirements.txt')
        
        return package_path

def deploy_lambda_function(
    function_name: str = "nrtaxai-av-scanner",
    region: str = "us-east-1",
    role_arn: str = None
) -> Dict[str, Any]:
    """Deploy or update Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Create deployment package
    package_path = create_lambda_package()
    
    try:
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=function_name)
            function_exists = True
        except lambda_client.exceptions.ResourceNotFoundException:
            function_exists = False
        
        if function_exists:
            # Update existing function
            with open(package_path, 'rb') as zip_file:
                response = lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=zip_file.read()
                )
            
            print(f"✅ Updated Lambda function: {function_name}")
            
        else:
            # Create new function
            if not role_arn:
                raise ValueError("role_arn is required for new function creation")
            
            with open(package_path, 'rb') as zip_file:
                response = lambda_client.create_function(
                    FunctionName=function_name,
                    Runtime='python3.9',
                    Role=role_arn,
                    Handler='av_scanner.lambda_handler',
                    Code={'ZipFile': zip_file.read()},
                    Description='NRTaxAI Antivirus Scanner',
                    Timeout=300,  # 5 minutes
                    MemorySize=1024,  # 1GB
                    Environment={
                        'Variables': {
                            'LOG_LEVEL': 'INFO'
                        }
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
