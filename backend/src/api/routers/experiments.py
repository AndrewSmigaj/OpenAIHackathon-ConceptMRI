#!/usr/bin/env python3
"""
Experiments API router - Expert route analysis and visualization.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pathlib import Path
from datetime import datetime
import json
import logging

from api.schemas import (
    AnalyzeRoutesRequest, AnalyzeClusterRoutesRequest, RouteAnalysisResponse,
    RouteDetailsResponse, ExpertDetailsResponse,
    LLMInsightsRequest, LLMInsightsResponse,
    ReductionRequest, ReductionResponse,
    ScaffoldStepRequest, ScaffoldStepResponse,
    TemporalCaptureRequest, TemporalCaptureResponse,
    TemporalLagDataRequest, TemporalLagPoint, TemporalLagDataResponse,
)
from api.dependencies import get_route_analysis_service, get_cluster_analysis_service, get_llm_insights_service, get_capture_service
from services.experiments.expert_route_analysis import ExpertRouteAnalysisService
from services.experiments.cluster_route_analysis import ClusterRouteAnalysisService
from services.experiments.llm_insights_service import LLMInsightsService
from services.probes.integrated_capture_service import IntegratedCaptureService

router = APIRouter()
logger = logging.getLogger(__name__)

# Resolve data lake path once
_data_lake_path = str(Path(__file__).resolve().parents[4] / "data" / "lake")


def _rebuild_output_nodes(
    result: dict,
    session_id: str,
    window_layers: list,
    output_grouping_axes: list,
) -> dict:
    """Strip existing Out:* nodes/links from cached result and rebuild with dynamic grouping."""
    from core.parquet_reader import read_records
    from schemas.tokens import ProbeRecord
    from services.experiments.output_category_nodes import build_output_category_layer

    # Strip Out:* nodes and links
    base_nodes = [n for n in result["nodes"] if not n["name"].startswith("Out:")]
    base_links = [l for l in result["links"] if not l["target"].startswith("Out:")]

    # Load token records from parquet
    session_path = Path(_data_lake_path) / session_id
    if not session_path.exists():
        session_path = Path(_data_lake_path) / f"session_{session_id}"
    token_records = read_records(str(session_path / "tokens.parquet"), ProbeRecord)

    # Reconstruct routes from cached node token data
    routes = {}
    for node in base_nodes:
        if not node.get("tokens"):
            continue
        for token_info in node["tokens"]:
            pid = token_info.get("probe_id")
            if not pid:
                continue
            # Each probe needs a route signature — use all nodes it appears in
            # We'll build a simple mapping: final-layer node -> probe_ids
            # The build_output_category_layer only needs routes to map probes to final nodes

    # Simpler approach: build a synthetic routes dict from final-layer nodes
    final_layer = max(window_layers)
    final_nodes = [n for n in base_nodes if n.get("layer") == final_layer]

    # Collect ALL probe_ids per final node (not just example tokens)
    # Use links to reconstruct: for each link ending at a final node, trace probe_ids
    # Actually, the node's token_count tells us how many probes, but tokens list is capped at 10
    # We need the full probe list — use token_records + the node membership

    # Build probe->final_node mapping from the full token_records
    # For cluster routes: use probe_assignments if available
    probe_assignments = result.get("probe_assignments", {})
    final_node_probes = {}

    if probe_assignments:
        # Use probe_assignments to map probes to final-layer clusters
        layer_key = str(final_layer)
        for probe_id, layers in probe_assignments.items():
            if layer_key in layers:
                cluster_id = layers[layer_key]
                node_name = f"L{final_layer}C{cluster_id}"
                if node_name not in final_node_probes:
                    final_node_probes[node_name] = []
                final_node_probes[node_name].append(probe_id)
    else:
        # For expert routes: use probe_ids field (complete list) or fall back to tokens (limited)
        for node in final_nodes:
            node_name = node["name"]
            if node.get("probe_ids"):
                final_node_probes[node_name] = node["probe_ids"]
            elif node.get("tokens"):
                final_node_probes[node_name] = [
                    t["probe_id"] for t in node["tokens"] if t.get("probe_id")
                ]

    # Build synthetic routes dict that build_output_category_layer expects
    routes = {}
    for node_name, probe_ids in final_node_probes.items():
        sig = node_name  # Single-node "route"
        routes[sig] = {
            "tokens": [{"probe_id": pid} for pid in probe_ids],
            "count": len(probe_ids),
            "avg_confidence": 0.0,
        }

    augmented_nodes, augmented_links, output_axes = build_output_category_layer(
        base_nodes, base_links, routes, token_records, window_layers,
        output_grouping_axes=output_grouping_axes,
    )

    result = dict(result)
    result["nodes"] = augmented_nodes
    result["links"] = augmented_links
    if output_axes:
        result["output_available_axes"] = output_axes

    return result


def _precompute_output_variants(result, session_id, window_layers, window_key, wdir):
    """Pre-compute all output axis combination variants and save to cache."""
    output_axes = result.get("output_available_axes")
    if not output_axes:
        return
    axis_ids = [a["id"] for a in output_axes]
    # Single axes
    for axis in axis_ids:
        variant = _rebuild_output_nodes(result, session_id, window_layers, [axis])
        (wdir / f"{window_key}__out_{axis}.json").write_text(json.dumps(variant))
    # Axis pairs
    for i, a1 in enumerate(axis_ids):
        for a2 in axis_ids[i + 1:]:
            sorted_pair = sorted([a1, a2])
            variant = _rebuild_output_nodes(result, session_id, window_layers, sorted_pair)
            key = f"{window_key}__out_{'__'.join(sorted_pair)}"
            (wdir / f"{key}.json").write_text(json.dumps(variant))
    logger.info(f"Pre-computed {len(axis_ids)} single + {len(axis_ids) * (len(axis_ids) - 1) // 2} pair output variants for {window_key}")


@router.post("/experiments/analyze-routes", response_model=RouteAnalysisResponse)
async def analyze_expert_routes(
    request: AnalyzeRoutesRequest,
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service)
):
    """Analyze expert routes for a session within specified window layers.

    Supports named clustering schemas:
    - clustering_schema: load cached result from a named schema (skip computation)
    - save_as: compute AND save result under this schema name
    """
    try:
        ids = request.session_ids or ([request.session_id] if request.session_id else [])
        window_key = f"w_{'_'.join(str(l) for l in request.window_layers)}"

        # Load from cached schema if requested
        if request.clustering_schema and ids:
            schema_dir = Path(_data_lake_path) / ids[0] / "clusterings" / request.clustering_schema
            wdir_cached = schema_dir / "expert_windows"
            cached_path = wdir_cached / f"{window_key}.json"
            if cached_path.exists():
                result = json.loads(cached_path.read_text())
                # Determine grouping axes: use requested, or default to first output axis
                grouping_axes = request.output_grouping_axes
                if not grouping_axes and result.get("output_available_axes"):
                    grouping_axes = [result["output_available_axes"][0]["id"]]
                if grouping_axes:
                    sorted_axes = sorted(grouping_axes)
                    variant_path = wdir_cached / f"{window_key}__out_{'__'.join(sorted_axes)}.json"
                    if variant_path.exists():
                        logger.info(f"Loading pre-computed expert variant: {variant_path.name}")
                        return json.loads(variant_path.read_text())
                    result = _rebuild_output_nodes(result, ids[0], request.window_layers, grouping_axes)
                return result

        filter_config_dict = None
        if request.filter_config:
            filter_config_dict = request.filter_config.dict(exclude_none=True)

        result = service.analyze_session_routes(
            session_id=request.session_id,
            session_ids=request.session_ids,
            window_layers=request.window_layers,
            filter_config=filter_config_dict,
            top_n_routes=request.top_n_routes,
            output_grouping_axes=request.output_grouping_axes,
        )

        # Auto-save if save_as provided
        if request.save_as and len(ids) == 1:
            schema_dir = Path(_data_lake_path) / ids[0] / "clusterings" / request.save_as
            wdir = schema_dir / "expert_windows"
            wdir.mkdir(parents=True, exist_ok=True)
            # Base file: apply first output axis (2 nodes) instead of raw cross-product
            save_result = result
            if result.get("output_available_axes"):
                first_axis = result["output_available_axes"][0]["id"]
                save_result = _rebuild_output_nodes(result, ids[0], request.window_layers, [first_axis])
            (wdir / f"{window_key}.json").write_text(json.dumps(save_result))
            # Save meta on first window
            meta_path = schema_dir / "meta.json"
            if not meta_path.exists():
                meta = {
                    "name": request.save_as,
                    "created_at": datetime.now().isoformat(),
                    "created_by": "claude_code",
                    "params": {"type": "expert_routes"},
                }
                meta_path.write_text(json.dumps(meta, indent=2))
            _precompute_output_variants(result, ids[0], request.window_layers, window_key, wdir)
            logger.info(f"Saved expert routes to schema: {request.save_as}/{window_key}")

        # Default to first output axis if none requested (always 2 nodes)
        if not request.output_grouping_axes and result.get("output_available_axes") and ids:
            first_axis = result["output_available_axes"][0]["id"]
            result = _rebuild_output_nodes(result, ids[0], request.window_layers, [first_axis])

        logger.info(f"Analyzed routes, found {result['statistics']['total_routes']} routes")
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Route analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Route analysis failed: {str(e)}")


@router.post("/experiments/analyze-cluster-routes", response_model=RouteAnalysisResponse)
async def analyze_cluster_routes(
    request: AnalyzeClusterRoutesRequest,
    service: ClusterRouteAnalysisService = Depends(get_cluster_analysis_service)
):
    """Analyze cluster routes for a session within specified window layers.

    Supports named clustering schemas:
    - clustering_schema: load cached result from a named schema (skip computation)
    - save_as: compute AND save result under this schema name
    """
    try:
        ids = request.session_ids or ([request.session_id] if request.session_id else [])
        window_key = f"w_{'_'.join(str(l) for l in request.window_layers)}"

        # Load from cached schema if requested
        if request.clustering_schema and ids:
            schema_dir = Path(_data_lake_path) / ids[0] / "clusterings" / request.clustering_schema
            wdir_cached = schema_dir / "cluster_windows"
            cached_path = wdir_cached / f"{window_key}.json"
            if cached_path.exists():
                result = json.loads(cached_path.read_text())
                # Determine grouping axes: use requested, or default to first output axis
                grouping_axes = request.output_grouping_axes
                if not grouping_axes and result.get("output_available_axes"):
                    grouping_axes = [result["output_available_axes"][0]["id"]]
                if grouping_axes:
                    sorted_axes = sorted(grouping_axes)
                    variant_path = wdir_cached / f"{window_key}__out_{'__'.join(sorted_axes)}.json"
                    if variant_path.exists():
                        logger.info(f"Loading pre-computed cluster variant: {variant_path.name}")
                        return json.loads(variant_path.read_text())
                    result = _rebuild_output_nodes(result, ids[0], request.window_layers, grouping_axes)
                return result

        # Compute fresh
        filter_config_dict = None
        if request.filter_config:
            filter_config_dict = request.filter_config.dict(exclude_none=True)

        # Resolve clustering config: explicit > schema meta.json > error
        if request.clustering_config:
            clustering_config_dict = request.clustering_config.dict(exclude_none=True)
        elif request.clustering_schema and ids:
            meta_path = Path(_data_lake_path) / ids[0] / "clusterings" / request.clustering_schema / "meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                clustering_config_dict = meta.get("params", {})
            else:
                raise HTTPException(status_code=400, detail=f"Schema '{request.clustering_schema}' not found and no clustering_config provided")
        else:
            raise HTTPException(status_code=400, detail="Either clustering_config or clustering_schema is required")

        result = service.analyze_session_cluster_routes(
            session_id=request.session_id,
            session_ids=request.session_ids,
            window_layers=request.window_layers,
            clustering_config=clustering_config_dict,
            filter_config=filter_config_dict,
            top_n_routes=request.top_n_routes,
            output_grouping_axes=request.output_grouping_axes,
        )

        # Auto-save if save_as provided
        if request.save_as and len(ids) == 1:
            schema_dir = Path(_data_lake_path) / ids[0] / "clusterings" / request.save_as
            wdir = schema_dir / "cluster_windows"
            wdir.mkdir(parents=True, exist_ok=True)
            # Base file: apply first output axis (2 nodes) instead of raw cross-product
            save_result = result
            if result.get("output_available_axes"):
                first_axis = result["output_available_axes"][0]["id"]
                save_result = _rebuild_output_nodes(result, ids[0], request.window_layers, [first_axis])
            (wdir / f"{window_key}.json").write_text(json.dumps(save_result))
            # Save meta on first window
            meta_path = schema_dir / "meta.json"
            if not meta_path.exists():
                meta = {
                    "name": request.save_as,
                    "created_at": datetime.now().isoformat(),
                    "created_by": "claude_code",
                    "params": clustering_config_dict,
                }
                meta_path.write_text(json.dumps(meta, indent=2))
            # Merge probe_assignments (accumulate layers across windows)
            if "probe_assignments" in result:
                pa_path = schema_dir / "probe_assignments.json"
                if pa_path.exists():
                    existing_pa = json.loads(pa_path.read_text())
                    for probe_id, layers in result["probe_assignments"].items():
                        if probe_id not in existing_pa:
                            existing_pa[probe_id] = {}
                        existing_pa[probe_id].update(layers)
                    pa_path.write_text(json.dumps(existing_pa))
                else:
                    pa_path.write_text(json.dumps(result["probe_assignments"]))
            _precompute_output_variants(result, ids[0], request.window_layers, window_key, wdir)
            logger.info(f"Saved cluster routes to schema: {request.save_as}/{window_key}")

        # Default to first output axis if none requested (always 2 nodes)
        if not request.output_grouping_axes and result.get("output_available_axes") and ids:
            first_axis = result["output_available_axes"][0]["id"]
            result = _rebuild_output_nodes(result, ids[0], request.window_layers, [first_axis])

        logger.info(f"Analyzed cluster routes, found {result['statistics']['total_routes']} routes")
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Cluster route analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cluster route analysis failed: {str(e)}")


@router.get("/experiments/route-details", response_model=RouteDetailsResponse)
async def get_route_details(
    session_id: str = Query(..., description="Session ID"),
    signature: str = Query(..., description="Route signature (e.g., L0E18→L1E11→L2E14)"),
    window_layers: str = Query(..., description="Comma-separated layers (e.g., 0,1,2)"),
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service)
):
    """Get detailed information about a specific expert route."""
    try:
        try:
            window_layers_list = [int(x.strip()) for x in window_layers.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid window_layers format")

        result = service.get_route_details(
            session_id=session_id,
            route_signature=signature,
            window_layers=window_layers_list
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Route details failed: {e}")
        raise HTTPException(status_code=500, detail=f"Route details failed: {str(e)}")


@router.get("/experiments/expert-details", response_model=ExpertDetailsResponse)
async def get_expert_details(
    session_id: str = Query(..., description="Session ID"),
    layer: int = Query(..., description="Layer number"),
    expert_id: int = Query(..., description="Expert ID"),
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service)
):
    """Get details about a specific expert's specialization."""
    try:
        result = service.get_expert_details(
            session_id=session_id,
            layer=layer,
            expert_id=expert_id
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Expert details failed: {e}")
        raise HTTPException(status_code=500, detail=f"Expert details failed: {str(e)}")


@router.post("/experiments/llm-insights", response_model=LLMInsightsResponse)
async def generate_llm_insights(
    request: LLMInsightsRequest,
    service: LLMInsightsService = Depends(get_llm_insights_service)
):
    """Generate LLM insights from expert routing data."""
    try:
        result = await service.analyze_routing_patterns(
            windows=request.windows,
            user_prompt=request.user_prompt,
            api_key=request.api_key,
            provider=request.provider
        )

        return LLMInsightsResponse(**result)

    except Exception as e:
        logger.error(f"LLM insights generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments/reduce", response_model=ReductionResponse)
async def reduce_embeddings(request: ReductionRequest):
    """On-demand dimensionality reduction for one or more sessions."""
    try:
        from services.features.reduction_service import ReductionService
        reducer = ReductionService(n_components=request.n_components)

        points = reducer.reduce_on_demand(
            session_ids=request.session_ids,
            layers=request.layers,
            data_lake_path=_data_lake_path,
            source=request.source,
            method=request.method,
            n_components=request.n_components,
        )

        logger.info(f"Reduced {len(points)} points for {len(request.session_ids)} sessions")
        return ReductionResponse(
            points=points,
            layers=request.layers,
            method=request.method,
            n_components=request.n_components,
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Reduction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reduction failed: {e}")


@router.post("/experiments/scaffold-step", response_model=ScaffoldStepResponse)
async def run_scaffold_step(
    request: ScaffoldStepRequest,
    service: LLMInsightsService = Depends(get_llm_insights_service)
) -> ScaffoldStepResponse:
    """Run a single scaffold step: prompt + data context -> LLM -> result."""
    try:
        result = await service.run_scaffold_step(
            prompt=request.prompt,
            data_sources=request.data_sources,
            output_type=request.output_type,
            expert_windows=request.expert_windows,
            cluster_windows=request.cluster_windows,
            previous_outputs=request.previous_outputs,
            api_key=request.api_key,
            provider=request.provider,
        )
        return ScaffoldStepResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Scaffold step failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments/temporal-capture", response_model=TemporalCaptureResponse)
async def run_temporal_capture(
    request: TemporalCaptureRequest,
    service: IntegratedCaptureService = Depends(get_capture_service),
):
    """Run a temporal basin transition experiment.

    Builds a sequence of sentences from two opposing clusters (basins),
    captures probes with KV cache chaining, and stores results in a new session.
    """
    import random
    import uuid
    import pandas as pd

    try:

        # Load probe assignments
        session_dir = Path(_data_lake_path) / request.session_id
        if not session_dir.exists():
            raise HTTPException(status_code=404, detail=f"Session '{request.session_id}' not found")

        # Try named schema first, then fallback to session-level file
        pa_path = None
        if request.clustering_schema:
            pa_path = session_dir / "clusterings" / request.clustering_schema / "probe_assignments.json"
        if not pa_path or not pa_path.exists():
            pa_path = session_dir / "probe_assignments.json"
        if not pa_path.exists():
            raise HTTPException(status_code=404, detail="No probe assignments found. Run cluster analysis first.")

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

            # Find regime boundary: first position where target_word appears in cumulative text
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
                "sequence_config": "custom",
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


@router.get("/experiments/temporal-runs/{session_id}")
async def get_temporal_runs(session_id: str):
    """List temporal runs for a source session."""
    runs_path = Path(_data_lake_path) / session_id / "temporal_runs.json"
    if not runs_path.exists():
        return []
    return json.loads(runs_path.read_text())


@router.post("/experiments/temporal-lag-data", response_model=TemporalLagDataResponse)
async def get_temporal_lag_data(request: TemporalLagDataRequest):
    """Compute basin axis projection for a temporal session.

    Projects each temporal probe's residual stream vector onto the axis
    between basin A and basin B centroids. Returns a scalar per position:
    0.0 = at basin A centroid, 1.0 = at basin B centroid.
    """
    import numpy as np
    import pandas as pd

    try:
        source_dir = Path(_data_lake_path) / request.source_session_id
        temporal_dir = Path(_data_lake_path) / request.temporal_session_id

        if not source_dir.exists():
            raise HTTPException(status_code=404, detail=f"Source session '{request.source_session_id}' not found")
        if not temporal_dir.exists():
            raise HTTPException(status_code=404, detail=f"Temporal session '{request.temporal_session_id}' not found")

        # 1. Load source session residual streams at basin_layer, target position only
        source_streams = pd.read_parquet(source_dir / "residual_streams.parquet")
        source_streams = source_streams[
            (source_streams["layer"] == request.basin_layer) &
            (source_streams["token_position"] == 1)  # target word only (0=context, 1=target)
        ]

        # 2. Load probe assignments from schema
        schema_dir = source_dir / "clusterings" / request.clustering_schema
        pa_path = schema_dir / "probe_assignments.json"
        if not pa_path.exists():
            raise HTTPException(status_code=404, detail=f"Schema '{request.clustering_schema}' not found")
        probe_assignments = json.loads(pa_path.read_text())

        # 3. Compute centroids for basin A and basin B
        basin_a_vectors = []
        basin_b_vectors = []
        layer_key = str(request.basin_layer)
        for _, row in source_streams.iterrows():
            pid = row["probe_id"]
            cluster = probe_assignments.get(pid, {}).get(layer_key)
            if cluster is None:
                continue
            vec = np.array(row["residual_stream"], dtype=np.float32)
            if cluster == request.basin_a_cluster_id:
                basin_a_vectors.append(vec)
            elif cluster == request.basin_b_cluster_id:
                basin_b_vectors.append(vec)

        if not basin_a_vectors or not basin_b_vectors:
            raise HTTPException(status_code=400, detail=f"No probes found in basins (A={len(basin_a_vectors)}, B={len(basin_b_vectors)})")

        centroid_a = np.mean(basin_a_vectors, axis=0)
        centroid_b = np.mean(basin_b_vectors, axis=0)

        # 4. Compute basin axis
        axis = centroid_b - centroid_a
        axis_length = float(np.linalg.norm(axis))
        if axis_length < 1e-8:
            raise HTTPException(status_code=400, detail="Basin centroids are too close — cannot compute axis projection")
        axis_norm = axis / axis_length

        # 5. Load temporal session data
        temporal_streams = pd.read_parquet(temporal_dir / "residual_streams.parquet")
        temporal_streams = temporal_streams[
            (temporal_streams["layer"] == request.basin_layer) &
            (temporal_streams["token_position"] == 1)
        ]
        temporal_tokens = pd.read_parquet(temporal_dir / "tokens.parquet")

        # 6. Load sentence texts from temporal_runs.json (handles expanding_cache_off cumulative text)
        runs_path = source_dir / "temporal_runs.json"
        sentence_texts = {}
        run_meta = {}
        if runs_path.exists():
            for run in json.loads(runs_path.read_text()):
                if run["new_session_id"] == request.temporal_session_id:
                    sentence_texts = run.get("sentence_texts", {})
                    run_meta = run
                    break

        # 7. Compute basin axis projection for each temporal probe
        # Join tokens and streams on probe_id, sort by sentence_index
        token_map = {}
        for _, row in temporal_tokens.iterrows():
            token_map[row["probe_id"]] = {
                "sentence_index": row.get("sentence_index", 0),
                "label": row.get("label", ""),
                "input_text": row.get("input_text", ""),
                "target_word": row.get("target_word", ""),
            }

        points = []
        for _, row in temporal_streams.iterrows():
            pid = row["probe_id"]
            if pid not in token_map:
                continue
            tinfo = token_map[pid]
            vec = np.array(row["residual_stream"], dtype=np.float32)
            proj = float(np.dot(vec - centroid_a, axis_norm) / axis_length)
            pos = tinfo["sentence_index"] if tinfo["sentence_index"] is not None else 0

            # Use individual sentence text from run metadata if available
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


@router.get("/experiments/health")
async def health_check():
    """Health check for experiments API."""
    return {"status": "healthy", "service": "expert_route_analysis"}
