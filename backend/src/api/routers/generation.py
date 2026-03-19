#!/usr/bin/env python3
"""
Generation API router - Sentence set generation and management.
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import logging

from api.schemas import (
    GenerateSentenceSetRequest, SentenceSetResponse,
    SentenceSetDetailResponse, SentenceSetListResponse
)
from services.generation.sentence_set import (
    load_sentence_set_by_name, list_available_sentence_sets, _entry_to_dict
)
from services.generation.sentence_generator import SentenceGenerator

router = APIRouter()
logger = logging.getLogger(__name__)

SENTENCE_SETS_DIR = str(Path(__file__).resolve().parents[4] / "data" / "sentence_sets")


@router.get("/generation/sentence-sets", response_model=SentenceSetListResponse)
async def list_sentence_sets():
    """List available sentence sets."""
    try:
        sets = list_available_sentence_sets(SENTENCE_SETS_DIR)
        return SentenceSetListResponse(sentence_sets=sets)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sentence sets: {e}")


@router.get("/generation/sentence-sets/{name}", response_model=SentenceSetDetailResponse)
async def get_sentence_set(name: str):
    """Load a specific sentence set by name."""
    try:
        ss = load_sentence_set_by_name(name, SENTENCE_SETS_DIR)
        return SentenceSetDetailResponse(
            name=ss.name,
            version=ss.version,
            target_word=ss.target_word,
            label_a=ss.label_a,
            label_b=ss.label_b,
            description_a=ss.description_a,
            description_b=ss.description_b,
            sentences_a=[_entry_to_dict(e) for e in ss.sentences_a],
            sentences_b=[_entry_to_dict(e) for e in ss.sentences_b],
            sentences_neutral=[_entry_to_dict(e) for e in ss.sentences_neutral],
            metadata=ss.metadata,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Sentence set '{name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load sentence set: {e}")


@router.post("/generation/sentence-sets/generate", response_model=SentenceSetResponse)
async def generate_sentence_set(request: GenerateSentenceSetRequest):
    """Generate a new sentence set via LLM."""
    try:
        generator = SentenceGenerator()
        ss = await generator.generate_sentence_set(
            name=request.name,
            target_word=request.target_word,
            label_a=request.label_a,
            label_b=request.label_b,
            description_a=request.description_a,
            description_b=request.description_b,
            count_per_group=request.count_per_group,
            neutral_count=request.neutral_count,
            api_key=request.api_key,
            provider=request.provider,
        )

        if request.save:
            from services.generation.sentence_set import save_sentence_set
            path = str(Path(SENTENCE_SETS_DIR) / f"{request.name}.json")
            save_sentence_set(ss, path)
            logger.info(f"Saved sentence set to {path}")

        return SentenceSetResponse(
            name=ss.name,
            version=ss.version,
            target_word=ss.target_word,
            label_a=ss.label_a,
            label_b=ss.label_b,
            count_a=len(ss.sentences_a),
            count_b=len(ss.sentences_b),
            count_neutral=len(ss.sentences_neutral),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")
