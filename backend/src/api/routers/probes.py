#!/usr/bin/env python3
"""
Probes API router - Session management and sentence experiment capture.
"""

from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
from typing import List, Dict
import json
import logging

from api.schemas import (
    ExecutionResponse, StatusResponse,
    SessionListResponse, SessionDetailResponse,
    SentenceExperimentRequest, SentenceExperimentResponse,
    ProbeExample,
)
from api.dependencies import get_capture_service
from services.probes.integrated_capture_service import IntegratedCaptureService, SessionState
from schemas.capture_manifest import CaptureManifest
from core.parquet_reader import read_records
from schemas.tokens import ProbeRecord

router = APIRouter()
logger = logging.getLogger(__name__)

from api.config import DATA_LAKE_PATH


@router.get("/probes/{session_id}/status", response_model=StatusResponse)
async def get_probe_session_status(
    session_id: str,
    service: IntegratedCaptureService = Depends(get_capture_service)
):
    """Get current status of probe session."""
    try:
        status = service.get_session_status(session_id)

        response_data = {
            "session_id": session_id,
            "state": status.state.value,
            "progress": {
                "completed": status.completed_pairs,
                "total": status.total_pairs,
                "failed": status.failed_pairs,
                "percent": status.progress_percent
            }
        }

        if status.state == SessionState.COMPLETED:
            manifest = service.finalize_session(session_id)

            session_dir = Path(service.data_lake_path) / session_id
            data_lake_paths = {
                "tokens": str(session_dir / "tokens.parquet"),
                "routing": str(session_dir / "routing.parquet"),
                "expert_output": str(session_dir / "embeddings.parquet"),
                "manifest": str(session_dir / "capture_manifest.parquet")
            }

            manifest_dict = {
                "session_name": manifest.session_name,
                "target_word": manifest.target_word,
                "labels": manifest.labels,
                "probe_count": manifest.probe_count,
                "created_at": manifest.created_at,
                "model_name": manifest.model_name
            }

            response_data["manifest"] = manifest_dict
            response_data["data_lake_paths"] = data_lake_paths

        return StatusResponse(**response_data)

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")


@router.get("/probes", response_model=List[SessionListResponse])
async def list_probe_sessions(
    service: IntegratedCaptureService = Depends(get_capture_service)
):
    """List all available probe sessions."""
    try:
        sessions = []
        sessions_dir = Path(service.data_lake_path) / "_sessions"

        if sessions_dir.exists():
            for session_file in sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        metadata = json.load(f)

                    sessions.append(SessionListResponse(
                        session_id=metadata["session_id"],
                        session_name=metadata["session_name"],
                        created_at=metadata["created_at"],
                        probe_count=metadata.get("completed_pairs", metadata.get("total_pairs", 0)),
                        target_word=metadata.get("target_word"),
                        labels=metadata.get("labels"),
                        state=metadata["state"]
                    ))
                except Exception as e:
                    logger.warning("Skipping session %s: %s", metadata.get("session_id", session_file.stem), e)
                    continue

        return sorted(sessions, key=lambda x: x.created_at, reverse=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/probes/{session_id}", response_model=SessionDetailResponse)
async def get_probe_session_details(
    session_id: str,
    service: IntegratedCaptureService = Depends(get_capture_service)
):
    """Get complete session details including manifest and data lake paths."""
    try:
        status = service.get_session_status(session_id)

        if status.state != SessionState.COMPLETED:
            raise HTTPException(status_code=400, detail="Session not completed yet")

        if session_id in service.active_sessions:
            manifest = service.finalize_session(session_id)
        else:
            # Load existing manifest from session metadata
            session_file = Path(service.sessions_dir) / f"{session_id}.json"
            if not session_file.exists():
                raise HTTPException(status_code=404, detail="Session metadata file not found")

            with open(session_file, 'r') as f:
                session_metadata = json.load(f)

            manifest = CaptureManifest(
                capture_session_id=session_metadata["session_id"],
                session_name=session_metadata["session_name"],
                target_word=session_metadata.get("target_word", ""),
                labels=session_metadata.get("labels", []),
                layers_captured=session_metadata.get("layers", [0, 1, 2]),
                probe_count=session_metadata["total_pairs"],
                created_at=session_metadata["created_at"],
                model_name=session_metadata.get("model_name", "gpt-oss-20b")
            )

        # Generate data lake paths
        session_dir = Path(service.data_lake_path) / session_id
        data_lake_paths = {
            "tokens": str(session_dir / "tokens.parquet"),
            "routing": str(session_dir / "routing.parquet"),
            "expert_output": str(session_dir / "embeddings.parquet"),
            "manifest": str(session_dir / "capture_manifest.parquet")
        }

        # Build manifest dict
        manifest_dict = {
            "capture_session_id": manifest.capture_session_id,
            "session_name": manifest.session_name,
            "target_word": manifest.target_word,
            "labels": manifest.labels,
            "layers_captured": manifest.layers_captured,
            "probe_count": manifest.probe_count,
            "created_at": manifest.created_at,
            "model_name": manifest.model_name
        }

        # Read tokens.parquet to build sentence list
        tokens_path = session_dir / "tokens.parquet"
        sentences = None
        if tokens_path.exists():
            try:
                from services.probes.scenario_actions import enrich_records_with_scenario_actions
                token_records = read_records(str(tokens_path), ProbeRecord)
                enrich_records_with_scenario_actions(token_records, session_dir)
                sentences = [
                    ProbeExample(
                        target_word=t.target_word,
                        label=t.label,
                        input_text=t.input_text,
                        probe_id=t.probe_id,
                        generated_text=getattr(t, 'generated_text', None),
                        output_category=getattr(t, 'output_category', None),
                        target_char_offset=getattr(t, 'target_char_offset', None),
                        turn_id=getattr(t, 'turn_id', None),
                        capture_type=getattr(t, 'capture_type', None),
                    )
                    for t in token_records
                ]
            except Exception as e:
                logger.warning(f"Failed to read tokens for sentences: {e}")

        return SessionDetailResponse(
            manifest=manifest_dict,
            data_lake_paths=data_lake_paths,
            labels=manifest.labels,
            target_word=manifest.target_word,
            sentences=sentences,
        )

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=f"Session not found or error: {str(ve)}")
    except FileNotFoundError as fe:
        raise HTTPException(status_code=404, detail=f"Session data files not found: {str(fe)}")
    except Exception as e:
        logger.error(f"Unexpected error for session {session_id}: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=404, detail=f"Session not found or error: {str(e)}")


@router.post("/probes/sentence-experiment", response_model=SentenceExperimentResponse)
async def run_sentence_experiment(
    request: SentenceExperimentRequest,
    service: IntegratedCaptureService = Depends(get_capture_service)
):
    """
    Run a sentence experiment: load a sentence set, capture each sentence
    through the model as a probe, and finalize the session.
    """
    try:
        from services.generation.sentence_set import load_sentence_set_by_name

        # Load sentence set
        sentence_sets_dir = str(Path(__file__).resolve().parents[4] / "data" / "sentence_sets")
        ss = load_sentence_set_by_name(request.sentence_set_name, sentence_sets_dir)

        # Collect sentences from all groups
        sentences = []
        labels = []
        for g in ss.groups:
            labels.append(g.label)
            for entry in g.sentences:
                sentences.append((entry, g.label))

        if not sentences:
            raise ValueError(f"Sentence set '{request.sentence_set_name}' has no sentences")

        # Create session
        session_name = request.session_name or f"sentence_{ss.name}"
        session_id = service.create_sentence_session(
            session_name=session_name,
            total_probes=len(sentences),
            target_word=ss.target_word,
            labels=labels,
            sentence_set_name=ss.name,
        )

        # Capture each sentence
        counts = {g.label: 0 for g in ss.groups}
        for entry, label in sentences:
            try:
                categories = getattr(entry, 'categories', None)

                service.capture_probe(
                    session_id=session_id,
                    input_text=entry.text,
                    target_word=entry.target_word,
                    label=label,
                    categories=categories,
                    generate_output=request.generate_output,
                )
                counts[label] += 1
            except Exception as e:
                logger.warning(f"Skipping failed sentence: {e}")
                continue

        # Finalize session
        service.finalize_session(session_id)

        total = sum(counts.values())
        counts_str = " + ".join(f"{c}{l}" for l, c in counts.items())
        logger.info(f"Sentence experiment complete: {session_id} ({counts_str})")
        return SentenceExperimentResponse(
            session_id=session_id,
            session_name=session_name,
            total_probes=total,
            labels=labels,
            counts=counts,
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Sentence set '{request.sentence_set_name}' not found")
    except Exception as e:
        logger.error(f"Sentence experiment failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sentence experiment failed: {e}")


# --- Generated Output Endpoints ---

@router.get("/probes/sessions/{session_id}/generated-outputs")
async def get_generated_outputs(session_id: str):
    """Read generated outputs for Claude Code to categorize."""
    import pandas as pd
    tokens_path = DATA_LAKE_PATH / session_id / "tokens.parquet"
    if not tokens_path.exists():
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' tokens not found")
    df = pd.read_parquet(tokens_path)
    cols = ["probe_id", "input_text", "label", "generated_text", "output_category"]
    available = [c for c in cols if c in df.columns]
    return df[available].to_dict(orient="records")


@router.post("/probes/sessions/{session_id}/output-categories")
async def update_output_categories(session_id: str, categories: Dict[str, Dict[str, str]]):
    """Write output categories back to tokens.parquet (Claude Code POSTs after analysis)."""
    import pandas as pd
    tokens_path = DATA_LAKE_PATH / session_id / "tokens.parquet"
    if not tokens_path.exists():
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' tokens not found")
    df = pd.read_parquet(tokens_path)
    for probe_id, cats in categories.items():
        mask = df['probe_id'] == probe_id
        for col, val in cats.items():
            if col not in df.columns:
                df[col] = None
            df.loc[mask, col] = val
    df.to_parquet(tokens_path, index=False)
    return {"updated": len(categories)}


# --- Clustering Schema Endpoints ---

@router.get("/probes/sessions/{session_id}/clusterings")
async def list_clusterings(session_id: str):
    """List available named clustering schemas for a session."""
    clusterings_dir = DATA_LAKE_PATH / session_id / "clusterings"
    if not clusterings_dir.exists():
        return {"clusterings": []}
    schemas = []
    for d in sorted(clusterings_dir.iterdir()):
        if d.is_dir() and (d / "meta.json").exists():
            meta = json.loads((d / "meta.json").read_text())
            schemas.append(meta)
    return {"clusterings": schemas}


@router.get("/probes/sessions/{session_id}/clusterings/{schema_name}")
async def load_clustering(session_id: str, schema_name: str):
    """Load a specific clustering schema (meta + probe_assignments + reports)."""
    schema_dir = DATA_LAKE_PATH / session_id / "clusterings" / schema_name
    if not schema_dir.exists():
        raise HTTPException(status_code=404, detail=f"Clustering '{schema_name}' not found")
    meta = json.loads((schema_dir / "meta.json").read_text())
    result: Dict = {"meta": meta}
    pa_path = schema_dir / "probe_assignments.json"
    if pa_path.exists():
        result["probe_assignments"] = json.loads(pa_path.read_text())
    rdir = schema_dir / "reports"
    if rdir.exists():
        result["reports"] = {f.stem: f.read_text() for f in sorted(rdir.glob("*.md"))}
    desc_path = schema_dir / "element_descriptions.json"
    if desc_path.exists():
        result["element_descriptions"] = json.loads(desc_path.read_text())
    return result


@router.post("/probes/sessions/{session_id}/clusterings/{schema_name}/element-descriptions")
async def save_element_descriptions(session_id: str, schema_name: str, body: Dict):
    """Save element descriptions (cluster labels, route labels) for a clustering schema."""
    schema_dir = DATA_LAKE_PATH / session_id / "clusterings" / schema_name
    if not schema_dir.exists():
        raise HTTPException(status_code=404, detail=f"Clustering '{schema_name}' not found")
    desc_path = schema_dir / "element_descriptions.json"
    # Merge with existing descriptions if any
    existing = json.loads(desc_path.read_text()) if desc_path.exists() else {}
    existing.update(body.get("descriptions", {}))
    desc_path.write_text(json.dumps(existing, indent=2))
    return {"saved": len(existing)}


@router.post("/probes/sessions/{session_id}/clusterings/{schema_name}/reports/{window_key}")
async def save_report(session_id: str, schema_name: str, window_key: str, body: Dict):
    """Save a Claude Code analysis report for a specific window."""
    reports_dir = DATA_LAKE_PATH / session_id / "clusterings" / schema_name / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"{window_key}.md").write_text(body["report"])
    return {"saved": f"{schema_name}/{window_key}"}
