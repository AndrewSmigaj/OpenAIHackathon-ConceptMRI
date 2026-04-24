#!/usr/bin/env python3
"""
Cluster route analysis and dimensionality reduction endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import json
import logging

from api.schemas import (
    AnalyzeClusterRoutesRequest, RouteAnalysisResponse,
    ReductionRequest, ReductionResponse,
)
from api.dependencies import get_cluster_analysis_service
from services.experiments.cluster_route_analysis import ClusterRouteAnalysisService
from api.config import DATA_LAKE_PATH
from api.routers.route_utils import _rebuild_output_nodes, _precompute_output_variants

router = APIRouter()
logger = logging.getLogger(__name__)


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
        if request.clustering_schema and ids and not request.last_occurrence_only and request.max_probes is None:
            schema_dir = DATA_LAKE_PATH / ids[0] / "clusterings" / request.clustering_schema
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
            meta_path = DATA_LAKE_PATH / ids[0] / "clusterings" / request.clustering_schema / "meta.json"
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
            steps=request.steps,
            top_n_routes=request.top_n_routes,
            output_grouping_axes=request.output_grouping_axes,
            max_examples_per_node=request.max_examples_per_node,
            last_occurrence_only=request.last_occurrence_only,
            max_probes=request.max_probes,
        )

        # Extract and strip internal clustering artifacts (non-JSON-serializable)
        _centroids = result.pop("_centroids", None)
        result.pop("_reducers", None)

        # Auto-save if save_as provided
        if request.save_as and len(ids) == 1:
            schema_dir = DATA_LAKE_PATH / ids[0] / "clusterings" / request.save_as
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
                    "last_occurrence_only": request.last_occurrence_only,
                    "max_probes": request.max_probes,
                    "steps": request.steps,
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
            # Save centroids in reduced space (merge across windows)
            if _centroids:
                centroids_path = schema_dir / "centroids.json"
                centroids_all = json.loads(centroids_path.read_text()) if centroids_path.exists() else {}
                for layer, cdict in _centroids.items():
                    centroids_all[str(layer)] = {
                        str(k): v.tolist() for k, v in cdict.items()
                    }
                centroids_path.write_text(json.dumps(centroids_all))

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


@router.post("/experiments/reduce", response_model=ReductionResponse)
async def reduce_embeddings(request: ReductionRequest):
    """On-demand dimensionality reduction for one or more sessions."""
    try:
        from services.features.reduction_service import ReductionService
        reducer = ReductionService(n_components=request.n_components)

        points = reducer.reduce_on_demand(
            session_ids=request.session_ids,
            layers=request.layers,
            data_lake_path=str(DATA_LAKE_PATH),
            source=request.source,
            method=request.method,
            n_components=request.n_components,
            steps=request.steps,
            last_occurrence_only=request.last_occurrence_only,
            max_probes=request.max_probes,
            n_neighbors=request.n_neighbors,
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
