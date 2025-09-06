#!/usr/bin/env python3
"""
Minimal error handling for Concept MRI demo recording.
Simple exception classes with clear messages for debugging.
"""


class ConceptMRIError(Exception):
    """Base exception for Concept MRI operations."""
    
    def __init__(self, message: str, context: dict = None):
        super().__init__(message)
        self.context = context or {}


class ModelLoadError(ConceptMRIError):
    """Failed to load GPT-OSS-20B model or tokenizer."""
    pass


class CaptureServiceError(ConceptMRIError):
    """Error during MoE capture operations."""
    pass


class GPUMemoryError(ConceptMRIError):
    """GPU out of memory or CUDA error."""
    pass


class SessionError(ConceptMRIError):
    """Session management error."""
    pass