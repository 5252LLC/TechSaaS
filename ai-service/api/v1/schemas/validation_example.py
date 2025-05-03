"""
Example schemas for request validation demonstration
"""

from marshmallow import Schema, fields, validate

class TextAnalysisSchema(Schema):
    """Schema for text analysis requests"""
    text = fields.String(required=True, validate=validate.Length(min=1, max=5000))
    model = fields.String(required=False, default="ollama/llama2")
    options = fields.Dict(keys=fields.String(), values=fields.Raw(), required=False)
    
class ImageAnalysisSchema(Schema):
    """Schema for image analysis requests"""
    image_url = fields.Url(required=True)
    analysis_type = fields.String(
        required=True,
        validate=validate.OneOf(['object_detection', 'captioning', 'classification'])
    )
    include_metadata = fields.Boolean(required=False, default=False)
    
class CompletionRequestSchema(Schema):
    """Schema for completion requests"""
    prompt = fields.String(required=True, validate=validate.Length(min=1, max=2048))
    max_tokens = fields.Integer(required=False, default=256, validate=validate.Range(min=1, max=4096))
    temperature = fields.Float(required=False, default=0.7, validate=validate.Range(min=0.0, max=1.0))
    model = fields.String(required=False, default="ollama/llama2")
