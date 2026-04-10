import { useState, useCallback, useMemo } from 'react'
import type { SessionDetailResponse, RouteAnalysisResponse } from '../../types/api'
import type { FilterState } from '../WordFilterPanel'
import type { GradientScheme } from '../../utils/colorBlending'
import type { SelectedCard } from '../../types/analysis'
import type { DynamicAxis } from '../../types/api'
import MultiSankeyView from '../charts/MultiSankeyView'
import SteppedTrajectoryPlot from '../charts/SteppedTrajectoryPlot'

import { LAYER_RANGES } from '../../constants/layerRanges'
import { convertFilterState } from '../../utils/filterState'

interface ClusterRoutesSectionProps {
  sessionIds: string[]
  sessionData: SessionDetailResponse | null
  filterState: FilterState
  primaryValues: string[]
  gradient: GradientScheme
  secondaryValues?: string[]
  secondaryGradient?: GradientScheme
  secondaryAxisId?: string
  outputPrimaryValues?: string[]
  outputGradient?: GradientScheme
  outputSecondaryValues?: string[]
  outputSecondaryGradient?: GradientScheme
  outputSecondaryAxisId?: string
  outputColorAxisId?: string
  outputGroupingAxes?: string[]
  shapeAxisId?: string
  shapeAxis?: DynamicAxis
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
  clusteringSchema?: string
  onRouteDataLoaded?: (routeDataMap: Record<string, RouteAnalysisResponse | null>) => void
  onCardSelect: (card: SelectedCard) => void
}

export default function ClusterRoutesSection({
  sessionIds,
  sessionData,
  filterState,
  primaryValues,
  gradient,
  secondaryValues,
  secondaryGradient,
  secondaryAxisId,
  outputPrimaryValues,
  outputGradient,
  outputSecondaryValues,
  outputSecondaryGradient,
  outputSecondaryAxisId,
  outputColorAxisId,
  outputGroupingAxes,
  shapeAxisId,
  shapeAxis,
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
  clusteringSchema,
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
    <div className="bg-white rounded-xl shadow-sm p-1">
      <div className="flex items-center gap-2 mb-1 px-1">
        <span className="text-xs font-semibold text-gray-900">Latent Space</span>
        <button
          onClick={() => {
            runAnalysis?.()
            runTrajectoryAnalysis?.()
          }}
          disabled={!runAnalysis || !runTrajectoryAnalysis}
          className="px-2 py-0.5 bg-blue-600 text-white text-[10px] font-medium rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          Run
        </button>
      </div>

      <div>
        <div className="bg-gray-50 rounded-lg p-1 mb-2">
          <MultiSankeyView
            sessionIds={sessionIds}
            sessionData={sessionData}
            filterState={filterState}
            primaryValues={primaryValues}
            gradient={gradient}
            secondaryValues={secondaryValues}
            secondaryGradient={secondaryGradient}
            secondaryAxisId={secondaryAxisId}
            outputPrimaryValues={outputPrimaryValues}
            outputGradient={outputGradient}
            outputSecondaryValues={outputSecondaryValues}
            outputSecondaryGradient={outputSecondaryGradient}
            outputSecondaryAxisId={outputSecondaryAxisId}
            outputColorAxisId={outputColorAxisId}
            outputGroupingAxes={outputGroupingAxes}
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
            clusteringSchema={clusteringSchema}
          />
        </div>

        {/* Stepped Trajectory Plot */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <SteppedTrajectoryPlot
            sessionIds={sessionIds}
            layers={memoizedLayers}
            colorLabelA={primaryValues[0] || ''}
            colorLabelB={primaryValues[1] || ''}
            gradient={gradient}
            primaryValues={primaryValues}
            secondaryColorAxisId={secondaryAxisId}
            secondaryValues={secondaryValues}
            shapeAxisId={shapeAxisId}
            shapeValues={shapeAxis?.values}
            source={embeddingSource}
            method={reductionMethod}
            sessionData={sessionData}
            filterConfig={convertFilterState(filterState)}
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
                    signature: `Trajectory: ${info.label || 'probe'} · ${info.target || ''}`,
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
