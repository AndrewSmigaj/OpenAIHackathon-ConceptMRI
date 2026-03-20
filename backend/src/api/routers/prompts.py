#!/usr/bin/env python3
"""
Prompts API router - Serve scaffold prompt templates from disk.
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import logging
from typing import List, Dict, Any

router = APIRouter()
logger = logging.getLogger(__name__)

# Resolve scaffolds directory relative to project root
_project_root = Path(__file__).resolve().parents[4]  # backend/src/api/routers -> project root
_scaffolds_dir = _project_root / "data" / "prompts" / "scaffolds"


@router.get("/prompts/scaffold-templates", response_model=List[Dict[str, Any]])
async def get_scaffold_templates() -> List[Dict[str, Any]]:
    """Read all JSON files from data/prompts/scaffolds/ and return as a list."""
    if not _scaffolds_dir.exists():
        logger.warning(f"Scaffolds directory not found: {_scaffolds_dir}")
        return []

    templates: List[Dict[str, Any]] = []
    for json_file in sorted(_scaffolds_dir.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            templates.append(data)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read scaffold template {json_file.name}: {e}")
            continue

    logger.info(f"Loaded {len(templates)} scaffold templates")
    return templates
