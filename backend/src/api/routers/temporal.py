#!/usr/bin/env python3
"""
Temporal basin capture and lag analysis endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
import json
import logging

from api.schemas import (
    TemporalCaptureRequest, TemporalCaptureResponse,
    TemporalLagDataRequest, TemporalLagPoint, TemporalLagDataResponse,
)
from api.dependencies import get_capture_service
from services.probes.integrated_capture_service import IntegratedCaptureService
from api.config import DATA_LAKE_PATH

router = APIRouter()
logger = logging.getLogger(__name__)

_temporal_capture_busy = False


def _run_temporal_capture_sync(
    request: TemporalCaptureRequest,
    service: IntegratedCaptureService,
) -> TemporalCaptureResponse:
    """Synchronous temporal capture — runs in a thread to avoid blocking the event loop."""
    import random
    import uuid
    import pandas as pd

    try:

        # Load probe assignments
        session_dir = DATA_LAKE_PATH / request.session_id
        if not session_dir.exists():
            raise HTTPException(status_code=404, detail=f"Session '{request.session_id}' not found")

        # Schema dir is the only source of truth for probe_assignments.
        # The session-root copy was removed because it was silently the
        # last-written schema's assignments (stale for every other schema).
        if not request.clustering_schema:
            raise HTTPException(status_code=400, detail="clustering_schema is required")
        pa_path = session_dir / "clusterings" / request.clustering_schema / "probe_assignments.json"
        if not pa_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"probe_assignments.json not found for schema '{request.clustering_schema}'. Build the schema via /cluster OP-1 first.",
            )

        probe_assignments = json.loads(pa_path.read_text())

        # Load tokens for sentence texts
        tokens_path = session_dir / "tokens.parquet"
        df = pd.read_parquet(tokens_path)
        probe_texts = {
            row["probe_id"]: {
                "input_text": row["input_text"],
                "target_word": row["target_word"],
                "label": row.get("label"),
            }
            for _, row in df.iterrows()
        }

        # Filter probes by basin cluster at specified layer
        layer_key = str(request.basin_layer)
        basin_a_probes = []
        basin_b_probes = []
        for probe_id, layers in probe_assignments.items():
            if layer_key not in layers:
                continue
            cluster_id = layers[layer_key]
            if cluster_id == request.basin_a_cluster_id and probe_id in probe_texts:
                basin_a_probes.append(probe_id)
            elif cluster_id == request.basin_b_cluster_id and probe_id in probe_texts:
                basin_b_probes.append(probe_id)

        if not basin_a_probes or not basin_b_probes:
            raise HTTPException(status_code=400, detail=f"Not enough probes in basins (A={len(basin_a_probes)}, B={len(basin_b_probes)})")

        # Sample and build sequence
        n = request.sentences_per_block
        random.shuffle(basin_a_probes)
        random.shuffle(basin_b_probes)
        selected_a = basin_a_probes[:n]
        selected_b = basin_b_probes[:n]

        if request.sequence_config == "block_ab":
            sequence = [(pid, "A") for pid in selected_a] + [(pid, "B") for pid in selected_b]
            regime_boundary = len(selected_a)
        elif request.sequence_config == "block_ba":
            sequence = [(pid, "B") for pid in selected_b] + [(pid, "A") for pid in selected_a]
            regime_boundary = len(selected_b)
        elif request.sequence_config == "block_aba":
            half_n = n // 2
            sequence = (
                [(pid, "A") for pid in selected_a[:half_n]]
                + [(pid, "B") for pid in selected_b]
                + [(pid, "A") for pid in selected_a[half_n:n]]
            )
            regime_boundary = half_n
        else:
            raise HTTPException(status_code=400, detail=f"Unknown sequence_config: {request.sequence_config}")

        temporal_run_id = f"temporal_{uuid.uuid4().hex[:8]}"

        if request.custom_sentences:
            # --- Custom sentences mode (word-by-word, joke experiments) ---
            target_word = request.custom_target_word
            if not target_word:
                target_word = probe_texts[next(iter(probe_texts))]["target_word"]

            # Use explicit boundary if provided, else auto-detect via target word
            if request.custom_regime_boundary is not None:
                regime_boundary = request.custom_regime_boundary
            else:
                regime_boundary = len(request.custom_sentences)
                cumulative_check = ""
                for i, sent in enumerate(request.custom_sentences):
                    cumulative_check += (" " if cumulative_check else "") + sent
                    if target_word.lower() in cumulative_check.lower():
                        regime_boundary = i
                        break

            new_session_id = service.create_sentence_session(
                session_name=f"temporal_{request.run_label or temporal_run_id}",
                total_probes=len(request.custom_sentences),
                target_word=target_word,
                labels=["A", "B"],
                experiment_id=temporal_run_id,
            )

            past_kv = None
            cumulative_text = ""
            for i, sentence in enumerate(request.custom_sentences):
                if request.sequence_config == "block_ba":
                    regime = "B" if i < regime_boundary else "A"
                else:
                    regime = "A" if i < regime_boundary else "B"
                logger.info(f"Temporal capture [{request.processing_mode}] custom {i+1}/{len(request.custom_sentences)} regime={regime}")

                if request.processing_mode == "expanding_cache_off":
                    cumulative_text += (" " if cumulative_text else "") + sentence
                    input_text = cumulative_text
                    use_cache = False
                    pass_kv = None
                elif request.processing_mode in ("expanding_cache_on", "single_cache_on"):
                    input_text = sentence
                    use_cache = True
                    pass_kv = past_kv
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown processing_mode: {request.processing_mode}")

                # Determine target_token_position: use target word if present, else last token
                has_target = target_word.lower() in input_text.lower()
                target_token_position = None  # let find_word_token_position resolve
                if not has_target:
                    token_ids = service.processor.tokenizer.encode(input_text, add_special_tokens=False)
                    target_token_position = len(token_ids) - 1

                source_categories = {"source_basin": regime, "custom_sentence": "true"}

                _, new_kv = service.capture_probe(
                    session_id=new_session_id,
                    input_text=input_text,
                    target_word=target_word,
                    target_token_position=target_token_position,
                    past_key_values=pass_kv,
                    use_cache=use_cache,
                    experiment_id=temporal_run_id,
                    sequence_id=temporal_run_id,
                    sentence_index=i,
                    label=regime,
                    categories=source_categories,
                    transition_step=regime_boundary,
                    generate_output=request.generate_output,
                )
                past_kv = new_kv

            service.finalize_session(new_session_id)

            sentence_texts = {str(i): s for i, s in enumerate(request.custom_sentences)}
            runs_path = session_dir / "temporal_runs.json"
            existing_runs = json.loads(runs_path.read_text()) if runs_path.exists() else []
            existing_runs.append({
                "temporal_run_id": temporal_run_id,
                "new_session_id": new_session_id,
                "processing_mode": request.processing_mode,
                "sequence_config": request.sequence_config,
                "basin_a_cluster_id": request.basin_a_cluster_id,
                "basin_b_cluster_id": request.basin_b_cluster_id,
                "basin_layer": request.basin_layer,
                "clustering_schema": request.clustering_schema,
                "sentences_per_block": len(request.custom_sentences),
                "regime_boundary": regime_boundary,
                "sequence_positions": len(request.custom_sentences),
                "sentence_texts": sentence_texts,
                "custom_sentences": True,
            })
            runs_path.write_text(json.dumps(existing_runs, indent=2))

            return TemporalCaptureResponse(
                temporal_run_id=temporal_run_id,
                new_session_id=new_session_id,
                sequence_positions=len(request.custom_sentences),
                regime_boundary=regime_boundary,
                processing_mode=request.processing_mode,
                basin_a_sentences=regime_boundary,
                basin_b_sentences=len(request.custom_sentences) - regime_boundary,
            )

        # --- Standard basin-based mode ---
        # Create new session for temporal data
        new_session_id = service.create_sentence_session(
            session_name=f"temporal_{request.run_label or temporal_run_id}",
            total_probes=len(sequence),
            target_word=probe_texts[sequence[0][0]]["target_word"],
            labels=["A", "B"],
            experiment_id=temporal_run_id,
        )

        # Run capture sequence
        past_kv = None
        cumulative_text = ""
        for i, (probe_id, regime) in enumerate(sequence):
            probe_info = probe_texts[probe_id]
            logger.info(f"Temporal capture [{request.processing_mode}] probe {i+1}/{len(sequence)} regime={regime}")

            if request.processing_mode == "expanding_cache_off":
                # Concatenate all sentences, no cache
                cumulative_text += (" " if cumulative_text else "") + probe_info["input_text"]
                input_text = cumulative_text
                use_cache = False
                pass_kv = None
            elif request.processing_mode == "expanding_cache_on":
                # Single sentence input, chain KV cache
                input_text = probe_info["input_text"]
                use_cache = True
                pass_kv = past_kv
            elif request.processing_mode == "single_cache_on":
                # Single sentence input, chain KV cache
                input_text = probe_info["input_text"]
                use_cache = True
                pass_kv = past_kv
            else:
                raise HTTPException(status_code=400, detail=f"Unknown processing_mode: {request.processing_mode}")

            # Source traceability: store which original probe and basin this came from
            source_categories = {
                "source_probe_id": probe_id,
                "source_basin": regime,
                "source_cluster_id": str(request.basin_a_cluster_id if regime == "A" else request.basin_b_cluster_id),
            }

            _, new_kv = service.capture_probe(
                session_id=new_session_id,
                input_text=input_text,
                target_word=probe_info["target_word"],
                past_key_values=pass_kv,
                use_cache=use_cache,
                experiment_id=temporal_run_id,
                sequence_id=temporal_run_id,
                sentence_index=i,
                label=regime,
                categories=source_categories,
                transition_step=regime_boundary,
                generate_output=request.generate_output,
            )
            past_kv = new_kv

        service.finalize_session(new_session_id)

        # Store temporal run metadata + sentence text mapping in source session
        sentence_texts = {
            str(i): probe_texts[pid]["input_text"]
            for i, (pid, _regime) in enumerate(sequence)
        }
        runs_path = session_dir / "temporal_runs.json"
        existing_runs = json.loads(runs_path.read_text()) if runs_path.exists() else []
        existing_runs.append({
            "temporal_run_id": temporal_run_id,
            "new_session_id": new_session_id,
            "processing_mode": request.processing_mode,
            "sequence_config": request.sequence_config,
            "basin_a_cluster_id": request.basin_a_cluster_id,
            "basin_b_cluster_id": request.basin_b_cluster_id,
            "basin_layer": request.basin_layer,
            "clustering_schema": request.clustering_schema,
            "sentences_per_block": request.sentences_per_block,
            "regime_boundary": regime_boundary,
            "sequence_positions": len(sequence),
            "sentence_texts": sentence_texts,
        })
        runs_path.write_text(json.dumps(existing_runs, indent=2))

        return TemporalCaptureResponse(
            temporal_run_id=temporal_run_id,
            new_session_id=new_session_id,
            sequence_positions=len(sequence),
            regime_boundary=regime_boundary,
            processing_mode=request.processing_mode,
            basin_a_sentences=len(selected_a),
            basin_b_sentences=len(selected_b),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Temporal capture failed: {e}")
        raise HTTPException(status_code=500, detail=f"Temporal capture failed: {str(e)}")


@router.post("/experiments/temporal-capture", response_model=TemporalCaptureResponse)
async def run_temporal_capture(
    request: TemporalCaptureRequest,
    service: IntegratedCaptureService = Depends(get_capture_service),
):
    """Run a temporal basin transition experiment.

    Runs the capture in a thread pool so the event loop stays free
    for health checks and frontend data requests.
    """
    import asyncio

    global _temporal_capture_busy
    if _temporal_capture_busy:
        raise HTTPException(status_code=503, detail="A temporal capture is already in progress")

    _temporal_capture_busy = True
    try:
        return await asyncio.to_thread(_run_temporal_capture_sync, request, service)
    finally:
        _temporal_capture_busy = False


@router.get("/experiments/temporal-runs/{session_id}")
async def get_temporal_runs(session_id: str):
    """List temporal runs for a source session."""
    runs_path = DATA_LAKE_PATH / session_id / "temporal_runs.json"
    if not runs_path.exists():
        return []
    return json.loads(runs_path.read_text())


@router.post("/experiments/temporal-lag-data", response_model=TemporalLagDataResponse)
async def get_temporal_lag_data(request: TemporalLagDataRequest):
    """Compute basin axis projection for a temporal session.

    Projects each temporal probe's residual stream vector onto the axis
    between basin A and basin B centroids in UMAP/PCA-reduced space
    (the same coordinate system where clustering happened).
    Returns a scalar per position: 0.0 = at basin A centroid, 1.0 = at basin B centroid.
    """
    import numpy as np
    import pandas as pd
    from sklearn.decomposition import PCA

    try:
        source_dir = DATA_LAKE_PATH / request.source_session_id
        temporal_dir = DATA_LAKE_PATH / request.temporal_session_id

        if not source_dir.exists():
            raise HTTPException(status_code=404, detail=f"Source session '{request.source_session_id}' not found")
        if not temporal_dir.exists():
            raise HTTPException(status_code=404, detail=f"Temporal session '{request.temporal_session_id}' not found")

        # 1. Load persisted centroids (in reduced/UMAP space)
        schema_dir = source_dir / "clusterings" / request.clustering_schema
        centroids_path = schema_dir / "centroids.json"
        if not centroids_path.exists():
            raise HTTPException(status_code=400,
                detail="Centroids not found — re-run clustering to generate them")
        all_centroids = json.loads(centroids_path.read_text())
        layer_key = str(request.basin_layer)
        if layer_key not in all_centroids:
            raise HTTPException(status_code=400,
                detail=f"No centroids for layer {request.basin_layer}")

        centroid_a = np.array(all_centroids[layer_key][str(request.basin_a_cluster_id)], dtype=np.float32)
        centroid_b = np.array(all_centroids[layer_key][str(request.basin_b_cluster_id)], dtype=np.float32)

        # 2. Re-fit reducer from source data (deterministic with random_state=42)
        meta_path = schema_dir / "meta.json"
        if not meta_path.exists():
            raise HTTPException(status_code=400, detail=f"Schema meta.json not found")
        meta = json.loads(meta_path.read_text())
        params = meta.get("params", {})
        reduction_method = params.get("reduction_method", "pca")
        reduction_dims = params.get("reduction_dimensions", 128)

        source_streams = pd.read_parquet(source_dir / "residual_streams.parquet")
        source_streams = source_streams[
            (source_streams["layer"] == request.basin_layer) &
            (source_streams["token_position"] == 1)
        ]
        source_raw = np.array([
            row["residual_stream"] for _, row in source_streams.iterrows()
        ], dtype=np.float32)

        actual_dims = min(reduction_dims, source_raw.shape[0] - 1, source_raw.shape[1])
        if actual_dims < 1:
            actual_dims = 1

        if reduction_method == "umap" and source_raw.shape[0] >= 4:
            try:
                import umap
                reducer = umap.UMAP(
                    n_components=actual_dims,
                    random_state=42,
                    n_neighbors=min(15, max(2, source_raw.shape[0] - 1)),
                    min_dist=0.1,
                )
                reducer.fit(source_raw)
            except Exception:
                reducer = PCA(n_components=actual_dims, random_state=42)
                reducer.fit(source_raw)
        else:
            reducer = PCA(n_components=actual_dims, random_state=42)
            reducer.fit(source_raw)

        # 3. Compute basin axis in reduced space
        axis = centroid_b - centroid_a
        axis_length = float(np.linalg.norm(axis))
        if axis_length < 1e-8:
            raise HTTPException(status_code=400, detail="Basin centroids are too close — cannot compute axis projection")
        axis_norm = axis / axis_length

        # 4. Load temporal session data
        temporal_streams = pd.read_parquet(temporal_dir / "residual_streams.parquet")
        temporal_streams = temporal_streams[
            (temporal_streams["layer"] == request.basin_layer) &
            (temporal_streams["token_position"] == 1)
        ]
        temporal_tokens = pd.read_parquet(temporal_dir / "tokens.parquet")

        # 5. Load sentence texts from temporal_runs.json
        runs_path = source_dir / "temporal_runs.json"
        sentence_texts = {}
        run_meta = {}
        if runs_path.exists():
            for run in json.loads(runs_path.read_text()):
                if run["new_session_id"] == request.temporal_session_id:
                    sentence_texts = run.get("sentence_texts", {})
                    run_meta = run
                    break

        # 6. Batch-reduce all temporal vectors through the re-fitted reducer
        token_map = {}
        for _, row in temporal_tokens.iterrows():
            token_map[row["probe_id"]] = {
                "sentence_index": row.get("sentence_index", 0),
                "label": row.get("label", ""),
                "input_text": row.get("input_text", ""),
                "target_word": row.get("target_word", ""),
            }

        raw_vecs = np.stack([
            np.array(row["residual_stream"], dtype=np.float32)
            for _, row in temporal_streams.iterrows()
        ])
        reduced_vecs = reducer.transform(raw_vecs)

        # 7. Project each reduced vector onto the basin axis
        points = []
        for idx, (_, row) in enumerate(temporal_streams.iterrows()):
            pid = row["probe_id"]
            if pid not in token_map:
                continue
            tinfo = token_map[pid]
            vec = reduced_vecs[idx]
            proj = float(np.dot(vec - centroid_a, axis_norm) / axis_length)
            pos = tinfo["sentence_index"] if tinfo["sentence_index"] is not None else 0

            sentence_text = sentence_texts.get(str(pos), tinfo["input_text"])

            points.append(TemporalLagPoint(
                position=pos,
                regime=tinfo["label"],
                projection=proj,
                sentence_text=sentence_text,
                probe_id=pid,
                target_word=tinfo["target_word"],
            ))

        points.sort(key=lambda p: p.position)

        return TemporalLagDataResponse(
            points=points,
            regime_boundary=run_meta.get("regime_boundary", len(points) // 2),
            processing_mode=run_meta.get("processing_mode", "unknown"),
            temporal_run_id=run_meta.get("temporal_run_id", ""),
            basin_separation=axis_length,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Temporal lag data computation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Temporal lag data computation failed: {str(e)}")
