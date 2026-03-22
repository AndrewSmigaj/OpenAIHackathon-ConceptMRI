import { useState, useCallback, useMemo } from 'react'
import type { SessionDetailResponse, AnalyzeRoutesRequest, RouteAnalysisResponse } from '../../types/api'
import type { FilterState } from '../WordFilterPanel'
import type { GradientScheme } from '../../utils/colorBlending'
import type { SelectedCard } from '../../types/analysis'
import type { DynamicAxis } from '../../types/api'
import MultiSankeyView from '../charts/MultiSankeyView'
import SteppedTrajectoryPlot from '../charts/SteppedTrajectoryPlot'
import { ChartBarIcon } from '../icons/Icons'
import { LAYER_RANGES } from '../../constants/layerRanges'

/**
 * Convert frontend FilterState to backend filter_config format.
 * Empty sets mean "include all" (no filtering), so we return undefined.
 */
function convertFilterState(
  filterState: FilterState,
  sessionData?: SessionDetailResponse | null
): AnalyzeRoutesRequest['filter_config'] {
  const filterConfig: any = {};

  if (filterState.labels.size > 0) {
    filterConfig.labels = Array.from(filterState.labels);
  }

  return Object.keys(filterConfig).length > 0 ? filterConfig : undefined;
}

interface ClusterRoutesSectionProps {
  sessionIds: string[]
  sessionData: SessionDetailResponse | null
  filterState: FilterState
  colorLabelA: string
  colorLabelB: string
  gradient: GradientScheme
  secondaryCategoryA?: string
  secondaryCategoryB?: string
  secondaryGradient?: GradientScheme
  secondaryAxisId?: string
  shapeAxisId?: string
  shapeAxis?: DynamicAxis
  primaryAxisValues?: string[]
  secondaryAxisValues?: string[]
  selectedRange: string
  onRangeChange: (range: string) => void
  layerClusterCounts: {[key: number]: number}
  clusteringMethod: string
  reductionDimensions: number
  embeddingSource: string
  reductionMethod: string
  useAllLayersSameClusters: boolean
  setUseAllLayersSameClusters: (value: boolean) => void
  globalClusterCount: number
  setGlobalClusterCount: (value: number) => void
  clusteringDimSubset: number[] | null
  onRouteDataLoaded?: (routeDataMap: Record<string, RouteAnalysisResponse | null>) => void
  onCardSelect: (card: SelectedCard) => void
}

export default function ClusterRoutesSection({
  sessionIds,
  sessionData,
  filterState,
  colorLabelA,
  colorLabelB,
  gradient,
  secondaryCategoryA,
  secondaryCategoryB,
  secondaryGradient,
  secondaryAxisId,
  shapeAxisId,
  shapeAxis,
  primaryAxisValues,
  secondaryAxisValues,
  selectedRange,
  onRangeChange,
  layerClusterCounts,
  clusteringMethod,
  reductionDimensions,
  embeddingSource,
  reductionMethod,
  useAllLayersSameClusters,
  setUseAllLayersSameClusters,
  globalClusterCount,
  setGlobalClusterCount,
  clusteringDimSubset,
  onRouteDataLoaded,
  onCardSelect
}: ClusterRoutesSectionProps) {
  const [runAnalysis, setRunAnalysis] = useState<(() => void) | null>(null)
  const [runTrajectoryAnalysis, setRunTrajectoryAnalysis] = useState<(() => void) | null>(null)

  // Memoize layers array to prevent infinite re-renders
  const memoizedLayers = useMemo(() => {
    return LAYER_RANGES[selectedRange as keyof typeof LAYER_RANGES]?.windows.map(w => w.layers).flat() || []
  }, [selectedRange])

  const handleVisualizationClick = useCallback((elementType: 'cluster' | 'trajectory', data: any) => {
    onCardSelect({
      type: elementType === 'cluster' ? 'cluster' : 'route',
      data
    })
  }, [onCardSelect])

  const handleSankeyAnalysisReady = useCallback((analysisFunction: () => void) => {
    setRunAnalysis(() => analysisFunction)
  }, [])

  const handleTrajectoryAnalysisReady = useCallback((analysisFunction: () => void) => {
    setRunTrajectoryAnalysis(() => analysisFunction)
  }, [])

  // Memoize clusteringConfig to prevent infinite re-renders
  const memoizedClusteringConfig = useMemo(() => {
    let effectiveLayerClusterCounts: {[key: number]: number};

    if (useAllLayersSameClusters) {
      // Use the global cluster count for all current window layers
      effectiveLayerClusterCounts = {};
      memoizedLayers.forEach(layer => {
        effectiveLayerClusterCounts[layer] = globalClusterCount;
      });
    } else {
      // Use the per-layer configuration
      effectiveLayerClusterCounts = layerClusterCounts;
    }

    return {
      reduction_dimensions: reductionDimensions,
      clustering_method: clusteringMethod,
      layer_cluster_counts: effectiveLayerClusterCounts,
      embedding_source: embeddingSource,
      reduction_method: reductionMethod,
      ...(clusteringDimSubset ? { clustering_dimensions: clusteringDimSubset } : {})
    };
  }, [reductionDimensions, clusteringMethod, layerClusterCounts, useAllLayersSameClusters, globalClusterCount, memoizedLayers, embeddingSource, reductionMethod, clusteringDimSubset])

  return (
    <div className="bg-white rounded-xl shadow-sm p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Latent Space Analysis</h3>
          <p className="text-xs text-gray-600 mt-1">Cluster trajectories and stepped trajectory visualization</p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => {
              runAnalysis?.()
              runTrajectoryAnalysis?.()
            }}
            disabled={!runAnalysis || !runTrajectoryAnalysis}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Run Analysis
          </button>
          <ChartBarIcon style={{ width: '12px', height: '12px' }} className="text-blue-600" />
        </div>
      </div>

      <div>
        {/* Trajectory Sankey - Clusters and Paths */}
        <div className="bg-gray-50 rounded-lg p-6 mb-4">
          <MultiSankeyView
            sessionIds={sessionIds}
            sessionData={sessionData}
            filterState={filterState}
            colorLabelA={colorLabelA}
            colorLabelB={colorLabelB}
            gradient={gradient}
            secondaryCategoryA={secondaryCategoryA}
            secondaryCategoryB={secondaryCategoryB}
            secondaryGradient={secondaryGradient}
            secondaryAxisId={secondaryAxisId}
            showAllRoutes={false}
            topRoutes={20}
            selectedRange={selectedRange}
            onRangeChange={onRangeChange}
            onNodeClick={(data) => handleVisualizationClick('cluster', data)}
            onLinkClick={(data) => handleVisualizationClick('trajectory', data)}
            onRouteDataLoaded={onRouteDataLoaded}
            mode="cluster"
            manualTrigger={true}
            onAnalysisReady={handleSankeyAnalysisReady}
            clusteringConfig={memoizedClusteringConfig}
          />
        </div>

        {/* Stepped Trajectory Plot */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <SteppedTrajectoryPlot
            sessionIds={sessionIds}
            layers={memoizedLayers}
            colorLabelA={colorLabelA}
            colorLabelB={colorLabelB}
            gradient={gradient}
            primaryValues={primaryAxisValues}
            secondaryColorAxisId={secondaryAxisId}
            secondaryValues={secondaryAxisValues}
            shapeAxisId={shapeAxisId}
            shapeValues={shapeAxis?.values}
            source={embeddingSource}
            method={reductionMethod}
            sessionData={sessionData}
            filterConfig={convertFilterState(filterState, sessionData)}
            nComponents={reductionDimensions}
            height={400}
            maxTrajectories={400}
            manualTrigger={true}
            onAnalysisReady={handleTrajectoryAnalysisReady}
            onPointClick={useCallback((info: { probe_id: string; target: string; label?: string }) => {
              // Look up the full sentence from session data
              const sentence = sessionData?.sentences?.find(s => s.probe_id === info.probe_id)
              if (sentence) {
                onCardSelect({
                  type: 'route',
                  data: {
                    _fullData: sentence,
                    name: info.target,
                    label: info.label,
                    tokens: [sentence],
                    example_tokens: [sentence],
                    signature: `Trajectory: ${info.probe_id.slice(0, 8)}`,
                    probe_id: info.probe_id,
                  }
                })
              }
            }, [sessionData, onCardSelect])}
          />
        </div>
      </div>
    </div>
  )
}
