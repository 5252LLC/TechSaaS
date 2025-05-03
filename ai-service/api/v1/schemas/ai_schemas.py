"""
AI Task Schemas

This module defines the request and response schemas for AI task endpoints,
providing validation and documentation for the AI API.
"""

from marshmallow import Schema, fields, validate
from flask_smorest import Blueprint, abort
from enum import Enum

class ChatMessageRole(str, Enum):
    """Valid roles for chat messages"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

class ChatMessageSchema(Schema):
    """Schema for individual chat messages"""
    role = fields.String(
        required=True, 
        validate=validate.OneOf([r.value for r in ChatMessageRole]),
        metadata={
            "description": "Role of the message sender (system, user, assistant, function)",
            "example": "user"
        }
    )
    content = fields.String(
        required=True,
        validate=validate.Length(min=1, max=32768),
        metadata={
            "description": "The message content",
            "example": "Tell me about artificial intelligence."
        }
    )
    name = fields.String(
        required=False,
        metadata={
            "description": "Name of the sender (used primarily for function role)",
            "example": "John Doe"
        }
    )

class ChatRequestSchema(Schema):
    """Schema for chat completion requests"""
    messages = fields.List(
        fields.Nested(ChatMessageSchema),
        required=True,
        validate=validate.Length(min=1),
        metadata={
            "description": "List of messages in the conversation",
            "example": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is artificial intelligence?"}
            ]
        }
    )
    model = fields.String(
        required=False,
        metadata={
            "description": "AI model to use for completion",
            "example": "ollama/llama2"
        }
    )
    temperature = fields.Float(
        required=False,
        validate=validate.Range(min=0.0, max=2.0),
        load_default=0.7,
        metadata={
            "description": "Controls randomness (0.0 = deterministic, 1.0 = creative)",
            "example": 0.7
        }
    )
    max_tokens = fields.Integer(
        required=False,
        validate=validate.Range(min=1, max=32768),
        load_default=1024,
        metadata={
            "description": "Maximum number of tokens to generate",
            "example": 1024
        }
    )
    stream = fields.Boolean(
        required=False,
        load_default=False,
        metadata={
            "description": "Whether to stream the response",
            "example": False
        }
    )
    conversation_id = fields.String(
        required=False,
        metadata={
            "description": "ID for tracking conversation history",
            "example": "conv_123456789"
        }
    )

class ChatResponseSchema(Schema):
    """Schema for chat completion responses"""
    id = fields.String(
        required=True,
        metadata={
            "description": "Unique identifier for the completion",
            "example": "cmpl-123456789"
        }
    )
    model = fields.String(
        required=True,
        metadata={
            "description": "Model used for completion",
            "example": "ollama/llama2"
        }
    )
    choices = fields.List(
        fields.Dict,
        required=True,
        metadata={
            "description": "List of completion choices",
            "example": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Artificial intelligence (AI) refers to systems or machines that mimic human intelligence to perform tasks and can iteratively improve themselves based on the information they collect."
                    },
                    "finish_reason": "stop",
                    "index": 0
                }
            ]
        }
    )
    usage = fields.Dict(
        required=True,
        metadata={
            "description": "Token usage statistics",
            "example": {
                "prompt_tokens": 25,
                "completion_tokens": 42,
                "total_tokens": 67
            }
        }
    )
    conversation_id = fields.String(
        required=False,
        metadata={
            "description": "ID for tracking conversation history",
            "example": "conv_123456789"
        }
    )

class CompletionRequestSchema(Schema):
    """Schema for text completion requests"""
    prompt = fields.String(
        required=True,
        validate=validate.Length(min=1, max=32768),
        metadata={
            "description": "The text prompt to complete",
            "example": "Write a poem about artificial intelligence:"
        }
    )
    model = fields.String(
        required=False,
        metadata={
            "description": "AI model to use for completion",
            "example": "ollama/llama2"
        }
    )
    temperature = fields.Float(
        required=False,
        validate=validate.Range(min=0.0, max=2.0),
        load_default=0.7,
        metadata={
            "description": "Controls randomness (0.0 = deterministic, 1.0 = creative)",
            "example": 0.7
        }
    )
    max_tokens = fields.Integer(
        required=False,
        validate=validate.Range(min=1, max=32768),
        load_default=1024,
        metadata={
            "description": "Maximum number of tokens to generate",
            "example": 1024
        }
    )
    stream = fields.Boolean(
        required=False,
        load_default=False,
        metadata={
            "description": "Whether to stream the response",
            "example": False
        }
    )

class CompletionResponseSchema(Schema):
    """Schema for text completion responses"""
    id = fields.String(
        required=True,
        metadata={
            "description": "Unique identifier for the completion",
            "example": "cmpl-123456789"
        }
    )
    model = fields.String(
        required=True,
        metadata={
            "description": "Model used for completion",
            "example": "ollama/llama2"
        }
    )
    choices = fields.List(
        fields.Dict,
        required=True,
        metadata={
            "description": "List of completion choices",
            "example": [
                {
                    "text": "Silicon minds with neural weave,\nIn data's ocean, patterns they perceive.\nLearning, growing, day by day,\nArtificial brilliance on display.",
                    "finish_reason": "stop",
                    "index": 0
                }
            ]
        }
    )
    usage = fields.Dict(
        required=True,
        metadata={
            "description": "Token usage statistics",
            "example": {
                "prompt_tokens": 8,
                "completion_tokens": 36,
                "total_tokens": 44
            }
        }
    )

class AnalysisType(str, Enum):
    """Types of text analysis"""
    SENTIMENT = "sentiment"
    ENTITIES = "entities"
    SUMMARIZATION = "summarization"
    KEYWORDS = "keywords"
    CLASSIFICATION = "classification"
    LANGUAGE_DETECTION = "language_detection"
    
class TextAnalysisRequestSchema(Schema):
    """Schema for text analysis requests"""
    text = fields.String(
        required=True,
        validate=validate.Length(min=1, max=32768),
        metadata={
            "description": "Text content to analyze",
            "example": "The latest quarterly report shows significant growth in our AI division, with revenue increasing by 27% year over year. Customer satisfaction remains high at 92%."
        }
    )
    analysis_type = fields.String(
        required=True,
        validate=validate.OneOf([t.value for t in AnalysisType]),
        metadata={
            "description": "Type of analysis to perform",
            "example": "sentiment"
        }
    )
    model = fields.String(
        required=False,
        metadata={
            "description": "AI model to use for analysis",
            "example": "ollama/llama2"
        }
    )
    options = fields.Dict(
        required=False,
        metadata={
            "description": "Additional options for the analysis",
            "example": {
                "detailed": True,
                "include_confidence": True
            }
        }
    )

class TextAnalysisResponseSchema(Schema):
    """Schema for text analysis responses"""
    id = fields.String(
        required=True,
        metadata={
            "description": "Unique identifier for the analysis",
            "example": "ana-123456789"
        }
    )
    analysis_type = fields.String(
        required=True,
        metadata={
            "description": "Type of analysis performed",
            "example": "sentiment"
        }
    )
    model = fields.String(
        required=True,
        metadata={
            "description": "Model used for analysis",
            "example": "ollama/llama2"
        }
    )
    result = fields.Dict(
        required=True,
        metadata={
            "description": "Analysis results",
            "example": {
                "sentiment": "positive",
                "score": 0.87,
                "details": {
                    "positivity": 0.92,
                    "negativity": 0.05,
                    "neutrality": 0.03
                }
            }
        }
    )
    usage = fields.Dict(
        required=True,
        metadata={
            "description": "Token usage statistics",
            "example": {
                "input_tokens": 32,
                "output_tokens": 15,
                "total_tokens": 47
            }
        }
    )

# Add response schemas for streaming endpoints
class StreamingChatResponseSchema(Schema):
    """Schema for streaming chat responses"""
    id = fields.String(
        required=True,
        metadata={
            "description": "Unique identifier for the completion",
            "example": "cmpl-123456789"
        }
    )
    model = fields.String(
        required=True,
        metadata={
            "description": "Model used for completion",
            "example": "ollama/llama2"
        }
    )
    delta = fields.Dict(
        required=True,
        metadata={
            "description": "Content delta for this chunk",
            "example": {
                "role": "assistant",
                "content": " Artificial"
            }
        }
    )
    finish_reason = fields.String(
        required=False,
        metadata={
            "description": "Reason for finishing (null while streaming, 'stop' when complete)",
            "example": None
        }
    )

# Batch processing schemas
class BatchProcessingRequestSchema(Schema):
    """Schema for batch processing requests"""
    inputs = fields.List(
        fields.String,
        required=True,
        validate=validate.Length(min=1, max=100),
        metadata={
            "description": "List of text inputs to process",
            "example": [
                "The customer service was excellent and I'm very satisfied.",
                "The product arrived damaged and customer service was unhelpful."
            ]
        }
    )
    task = fields.String(
        required=True,
        validate=validate.OneOf(["completion", "chat", "analysis"]),
        metadata={
            "description": "The task to perform on each input",
            "example": "analysis"
        }
    )
    task_params = fields.Dict(
        required=True,
        metadata={
            "description": "Parameters for the specified task",
            "example": {
                "analysis_type": "sentiment",
                "model": "ollama/llama2"
            }
        }
    )
    callback_url = fields.Url(
        required=False,
        metadata={
            "description": "Optional webhook URL for async completion notification",
            "example": "https://example.com/webhook/callback"
        }
    )

class BatchProcessingResponseSchema(Schema):
    """Schema for batch processing responses"""
    batch_id = fields.String(
        required=True,
        metadata={
            "description": "Unique identifier for the batch job",
            "example": "batch-123456789"
        }
    )
    status = fields.String(
        required=True,
        validate=validate.OneOf(["pending", "processing", "complete", "failed"]),
        metadata={
            "description": "Current status of the batch job",
            "example": "pending"
        }
    )
    task = fields.String(
        required=True,
        metadata={
            "description": "The task being performed",
            "example": "analysis"
        }
    )
    total_inputs = fields.Integer(
        required=True,
        metadata={
            "description": "Total number of inputs in the batch",
            "example": 2
        }
    )
    completed = fields.Integer(
        required=True,
        metadata={
            "description": "Number of completed inputs",
            "example": 0
        }
    )
    estimated_completion = fields.String(
        required=False,
        metadata={
            "description": "Estimated completion time (ISO format)",
            "example": "2025-05-03T15:22:31Z"
        }
    )
