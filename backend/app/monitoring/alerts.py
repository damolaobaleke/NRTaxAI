"""
CloudWatch Alerts Configuration
"""

import boto3
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()


class AlertManager:
    """Manage CloudWatch alarms"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.sns_client = boto3.client('sns')
    
    def create_alarms(self, project_name: str = "nrtaxai"):
        """Create all CloudWatch alarms"""
        
        alarms = [
            # ECS CPU Utilization
            {
                "AlarmName": f"{project_name}-ecs-cpu-high",
                "ComparisonOperator": "GreaterThanThreshold",
                "EvaluationPeriods": 2,
                "MetricName": "CPUUtilization",
                "Namespace": "AWS/ECS",
                "Period": 300,
                "Statistic": "Average",
                "Threshold": 70.0,
                "ActionsEnabled": True,
                "AlarmDescription": "Alert when ECS CPU > 70%",
                "Dimensions": [
                    {"Name": "ServiceName", "Value": f"{project_name}-service"},
                    {"Name": "ClusterName", "Value": f"{project_name}-cluster"}
                ]
            },
            
            # ECS Memory Utilization
            {
                "AlarmName": f"{project_name}-ecs-memory-high",
                "ComparisonOperator": "GreaterThanThreshold",
                "EvaluationPeriods": 2,
                "MetricName": "MemoryUtilization",
                "Namespace": "AWS/ECS",
                "Period": 300,
                "Statistic": "Average",
                "Threshold": 80.0,
                "ActionsEnabled": True,
                "AlarmDescription": "Alert when ECS Memory > 80%"
            },
            
            # RDS CPU Utilization
            {
                "AlarmName": f"{project_name}-rds-cpu-high",
                "ComparisonOperator": "GreaterThanThreshold",
                "EvaluationPeriods": 2,
                "MetricName": "CPUUtilization",
                "Namespace": "AWS/RDS",
                "Period": 300,
                "Statistic": "Average",
                "Threshold": 80.0,
                "ActionsEnabled": True,
                "AlarmDescription": "Alert when RDS CPU > 80%",
                "Dimensions": [
                    {"Name": "DBInstanceIdentifier", "Value": f"{project_name}-postgres"}
                ]
            },
            
            # RDS Free Storage
            {
                "AlarmName": f"{project_name}-rds-storage-low",
                "ComparisonOperator": "LessThanThreshold",
                "EvaluationPeriods": 1,
                "MetricName": "FreeStorageSpace",
                "Namespace": "AWS/RDS",
                "Period": 300,
                "Statistic": "Average",
                "Threshold": 10737418240,  # 10GB in bytes
                "ActionsEnabled": True,
                "AlarmDescription": "Alert when RDS free storage < 10GB",
                "Dimensions": [
                    {"Name": "DBInstanceIdentifier", "Value": f"{project_name}-postgres"}
                ]
            },
            
            # Lambda Errors
            {
                "AlarmName": f"{project_name}-lambda-errors-high",
                "ComparisonOperator": "GreaterThanThreshold",
                "EvaluationPeriods": 1,
                "MetricName": "Errors",
                "Namespace": "AWS/Lambda",
                "Period": 300,
                "Statistic": "Sum",
                "Threshold": 10.0,
                "ActionsEnabled": True,
                "AlarmDescription": "Alert when Lambda errors > 10 in 5 minutes"
            },
            
            # WAF Blocked Requests
            {
                "AlarmName": f"{project_name}-waf-blocked-requests-high",
                "ComparisonOperator": "GreaterThanThreshold",
                "EvaluationPeriods": 2,
                "MetricName": "BlockedRequests",
                "Namespace": "AWS/WAFV2",
                "Period": 300,
                "Statistic": "Sum",
                "Threshold": 100.0,
                "ActionsEnabled": True,
                "AlarmDescription": "Alert when WAF blocks > 100 requests in 5 minutes"
            },
            
            # API Gateway 5xx Errors
            {
                "AlarmName": f"{project_name}-api-5xx-errors",
                "ComparisonOperator": "GreaterThanThreshold",
                "EvaluationPeriods": 1,
                "MetricName": "5XXError",
                "Namespace": "AWS/ApiGateway",
                "Period": 60,
                "Statistic": "Sum",
                "Threshold": 5.0,
                "ActionsEnabled": True,
                "AlarmDescription": "Alert on API 5xx errors"
            }
        ]
        
        for alarm_config in alarms:
            try:
                self.cloudwatch.put_metric_alarm(**alarm_config)
                logger.info("Alarm created", alarm_name=alarm_config["AlarmName"])
            except Exception as e:
                logger.error("Failed to create alarm", 
                           alarm_name=alarm_config["AlarmName"],
                           error=str(e))


# Alarm configuration
ALARM_CONFIG = {
    "sns_topic_arn": "arn:aws:sns:us-east-1:*:nrtaxai-alerts",
    
    "critical_alarms": [
        "rds-storage-low",
        "rds-cpu-high",
        "ecs-memory-high"
    ],
    
    "warning_alarms": [
        "ecs-cpu-high",
        "lambda-errors-high",
        "waf-blocked-requests-high"
    ],
    
    "notification_channels": {
        "critical": ["email:ops@nrtaxai.com", "sms:+1234567890"],
        "warning": ["email:dev@nrtaxai.com"],
        "info": ["slack:#alerts"]
    }
}
