#!/usr/bin/env python3
"""
Probe ID generation utilities for Concept MRI.
Simple UUID-based probe identifiers for capture phase only.
"""

import uuid


def generate_probe_id(prefix: str = "probe") -> str:
    """
    Generate unique probe identifier for single context-target pair capture.
    
    Args:
        prefix: Optional prefix for the probe ID
        
    Returns:
        Unique probe ID like "probe_a1b2c3d4"
    """
    uuid_part = uuid.uuid4().hex[:8]
    return f"{prefix}_{uuid_part}"


def generate_capture_id(prefix: str = "capture") -> str:
    """
    Generate unique capture identifier for collections of related probes.
    
    Args:
        prefix: Optional prefix for the capture ID
        
    Returns:
        Unique capture ID like "capture_a1b2c3d4"
    """
    uuid_part = uuid.uuid4().hex[:8]
    return f"{prefix}_{uuid_part}"