#!/usr/bin/env python3
"""
Centralized configuration for the ConceptMRI backend.
"""

import os
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]  # config.py → api/ → src/ → backend/ → project_root
DATA_LAKE_PATH = Path(os.environ.get("DATA_LAKE_PATH", str(_project_root / "data" / "lake")))
