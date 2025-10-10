variable "project_name" { type = string }
variable "environment" { type = string }
variable "alb_arn" { type = string }

# WAF Web ACL
resource "aws_wafv2_web_acl" "main" {
  name = "${var.project_name}-waf"
  scope = "REGIONAL"
  
  default_action {
    allow {}
  }
  
  # Rate Limiting
  rule {
    name = "RateLimitRule"
    priority = 1
    
    action {
      block {}
    }
    
    statement {
      rate_based_statement {
        limit = 2000
        aggregate_key_type = "IP"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "RateLimitRule"
      sampled_requests_enabled = true
    }
  }
  
  # AWS Managed Rules - Core Rule Set
  rule {
    name = "AWSManagedRulesCommonRuleSet"
    priority = 2
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name = "AWSManagedRulesCommonRuleSet"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled = true
    }
  }
  
  # AWS Managed Rules - Known Bad Inputs
  rule {
    name = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 3
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled = true
    }
  }
  
  # SQL Injection Protection
  rule {
    name = "SQLInjectionRule"
    priority = 4
    
    action {
      block {}
    }
    
    statement {
      sqli_match_statement {
        field_to_match {
          all_query_arguments {}
        }
        
        text_transformation {
          priority = 0
          type = "URL_DECODE"
        }
        
        text_transformation {
          priority = 1
          type = "HTML_ENTITY_DECODE"
        }
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "SQLInjectionRule"
      sampled_requests_enabled = true
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name = "${var.project_name}-waf"
    sampled_requests_enabled = true
  }
}

# Associate WAF with ALB
resource "aws_wafv2_web_acl_association" "main" {
  resource_arn = var.alb_arn
  web_acl_arn = aws_wafv2_web_acl.main.arn
}

output "web_acl_id" {
  value = aws_wafv2_web_acl.main.id
}

output "web_acl_arn" {
  value = aws_wafv2_web_acl.main.arn
}
