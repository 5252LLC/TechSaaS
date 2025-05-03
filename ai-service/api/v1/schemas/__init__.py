"""
Schema definitions for API request and response validation
"""

from marshmallow import Schema, fields, validate, ValidationError


class AnalyzeRequestSchema(Schema):
    """Schema for content analysis requests"""
    content = fields.String(required=True, validate=validate.Length(min=1, max=50000), 
                           description="Text content to analyze")
    task = fields.String(required=False, validate=validate.OneOf(
        ["summarize", "categorize", "extract_entities", "sentiment", "keywords"]), 
                        default="summarize", description="Analysis task type")
    model = fields.String(required=False, description="AI model to use for analysis")
    options = fields.Dict(required=False, description="Additional analysis options")


class ChatRequestSchema(Schema):
    """Schema for chat message requests"""
    message = fields.String(required=True, validate=validate.Length(min=1, max=10000), 
                           description="User message text")
    history = fields.List(fields.Dict(keys=fields.Str(), values=fields.Str()), 
                         required=False, description="Previous conversation history")
    model = fields.String(required=False, description="AI model to use for chat")
    options = fields.Dict(required=False, description="Additional chat options")


class CompletionRequestSchema(Schema):
    """Schema for text completion requests"""
    prompt = fields.String(required=True, validate=validate.Length(min=1, max=10000), 
                          description="Text prompt for completion")
    max_tokens = fields.Integer(required=False, validate=validate.Range(min=1, max=100000), 
                               description="Maximum tokens to generate")
    temperature = fields.Float(required=False, validate=validate.Range(min=0.0, max=2.0), 
                              description="Temperature for sampling (0.0-2.0)")
    model = fields.String(required=False, description="AI model to use for completion")
    options = fields.Dict(required=False, description="Additional completion options")


class MultimodalAnalysisRequestSchema(Schema):
    """Schema for multimodal content analysis requests"""
    content_url = fields.String(required=True, description="URL to content or base64 encoded data")
    content_type = fields.String(required=True, validate=validate.OneOf(
        ["image", "video", "audio", "text", "mixed"]), description="Content type")
    analysis_type = fields.String(required=True, validate=validate.OneOf(
        ["object_detection", "scene_recognition", "ocr", "transcription", 
         "facial_recognition", "sentiment_analysis", "comprehensive"]),
                                 description="Type of analysis to perform")
    options = fields.Dict(required=False, description="Additional analysis options")


class MultimodalJobStatusSchema(Schema):
    """Schema for multimodal job status responses"""
    job_id = fields.String(required=True, description="Unique job identifier")
    status = fields.String(required=True, validate=validate.OneOf(
        ["submitted", "processing", "completed", "failed", "timeout"]),
                          description="Current job status")
    progress = fields.Integer(required=False, validate=validate.Range(min=0, max=100),
                             description="Progress percentage (0-100)")
    message = fields.String(required=False, description="Status message")
    estimated_completion_time = fields.String(required=False, 
                                             description="Estimated time to completion")


class MultimodalResultSchema(Schema):
    """Schema for multimodal analysis results"""
    job_id = fields.String(required=True, description="Unique job identifier")
    status = fields.String(required=True, 
                          description="Job status (should be 'completed' for results)")
    content_type = fields.String(required=True, description="Type of content analyzed")
    analysis_type = fields.String(required=True, description="Type of analysis performed")
    results = fields.Dict(required=True, description="Analysis results")
    processing_time = fields.String(required=False, description="Time taken for processing")
    billing = fields.Dict(required=False, description="Billing information")


class ModelReloadSchema(Schema):
    """Schema for model reload requests"""
    model_id = fields.String(required=False, description="Specific model ID to reload")


class LogRequestSchema(Schema):
    """Schema for log retrieval requests"""
    lines = fields.Integer(required=False, default=100, validate=validate.Range(min=1, max=1000),
                          description="Number of log lines to return")
    level = fields.String(required=False, default="INFO", validate=validate.OneOf(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]), 
                         description="Minimum log level")
    service = fields.String(required=False, description="Filter logs by service component")


class UsageQuerySchema(Schema):
    """Schema for usage data query parameters"""
    period = fields.String(required=False, default="current", validate=validate.OneOf(
        ["current", "previous", "all"]), description="Billing period")
    format = fields.String(required=False, default="json", validate=validate.OneOf(
        ["json", "csv", "pdf"]), description="Response format")
    detailed = fields.Boolean(required=False, default=False, 
                             description="Include detailed breakdown")


class APIKeySchema(Schema):
    """Schema for API key management"""
    name = fields.String(required=True, description="Name for the API key")
    expiration = fields.DateTime(required=False, description="Expiration date (optional)")
    permissions = fields.List(fields.String(), required=False, 
                             description="List of permissions for this key")
    tier = fields.String(required=False, default="basic", validate=validate.OneOf(
        ["basic", "pro", "enterprise"]), description="Access tier for the key")


class CustomConnectorSchema(Schema):
    """Schema for custom API connector configuration"""
    provider = fields.String(required=True, description="Provider name (e.g., 'openai', 'anthropic')")
    api_key = fields.String(required=True, description="API key for the service")
    base_url = fields.URL(required=False, description="Base URL override (optional)")
    default_model = fields.String(required=False, description="Default model to use")
    config = fields.Dict(required=False, description="Additional provider-specific configuration")
