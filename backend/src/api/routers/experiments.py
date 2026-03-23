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

        clustering_config_dict = request.clustering_config.dict(exclude_none=True)

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
            # Save probe_assignments
            if "probe_assignments" in result:
                (schema_dir / "probe_assignments.json").write_text(
                    json.dumps(result["probe_assignments"]))
            _precompute_output_variants(result, ids[0], request.window_layers, window_key, wdir)
            logger.info(f"Saved cluster routes to schema: {request.save_as}/{window_key}")

        # Default to first output axis if none requested (always 2 nodes)
        if not request.output_grouping_axes and result.get("output_available_axes") and ids:
            first_axis = result["output_available_axes"][0]["id"]
            result = _rebuild_output_nodes(result, ids[0], request.window_layers, [first_axis])

        logger.info(f"Analyzed cluster routes, found {result['statistics']['total_routes']} routes")
        return result

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
                transition_step=regime_boundary,
                generate_output=request.generate_output,
            )
            past_kv = new_kv

        service.finalize_session(new_session_id)

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


@router.get("/experiments/health")
async def health_check():
    """Health check for experiments API."""
    return {"status": "healthy", "service": "expert_route_analysis"}
