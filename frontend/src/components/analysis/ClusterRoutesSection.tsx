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
  steps?: number[] | null
  setSteps?: (steps: number[] | null) => void
  availableSteps?: number[]
  lastOccurrenceOnly?: boolean
  setLastOccurrenceOnly?: (value: boolean) => void
  maxProbes?: number | null
  setMaxProbes?: (value: number | null) => void
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
  steps,
  setSteps,
  availableSteps,
  lastOccurrenceOnly,
  setLastOccurrenceOnly,
  maxProbes,
  setMaxProbes,
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

  // Size of the probe pool after the `steps` + `lastOccurrenceOnly` filters
  // — the slider's upper bound. Mirrors backend `pick_last_occurrence` logic:
  // group by (input_text, target_word), keep the probe with the max
  // target_char_offset; probes with no offset are always kept.
  const filteredProbeCount = useMemo(() => {
    let sentences = sessionData?.sentences || []
    if (steps && steps.length > 0) {
      sentences = sentences.filter(s => s.step != null && steps.includes(s.step))
    }
    if (lastOccurrenceOnly) {
      const best = new Map<string, number>()
      let noOffset = 0
      for (const s of sentences) {
        if (s.target_char_offset == null) {
          noOffset += 1
          continue
        }
        const key = `${s.input_text}|${s.target_word}`
        const cur = best.get(key)
        if (cur == null || s.target_char_offset > cur) best.set(key, s.target_char_offset)
      }
      return best.size + noOffset
    }
    return sentences.length
  }, [sessionData, steps, lastOccurrenceOnly])

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
      ...(clusteringDimSubset ? { clustering_dimensions: clusteringDimSubset } : {}),
    };
  }, [reductionDimensions, clusteringMethod, layerClusterCounts, useAllLayersSameClusters, globalClusterCount, memoizedLayers, embeddingSource, reductionMethod, clusteringDimSubset])

  return (
    <div className="bg-white rounded-xl shadow-sm p-1">
      <div className="flex items-center gap-2 mb-1 px-1">
        <span className="text-xs font-semibold text-gray-900">Clusters & Routes</span>
        <span className="text-[9px] text-gray-400 italic">hierarchical clustering on UMAP-reduced residual stream</span>
        {availableSteps && availableSteps.length > 1 && setSteps && (
          <div className="flex items-center gap-1 ml-2">
            <span className="text-[10px] text-gray-400">Steps</span>
            <select
              value={steps === null ? 'all' : JSON.stringify(steps)}
              onChange={e => {
                const v = e.target.value
                setSteps(v === 'all' ? null : JSON.parse(v))
              }}
              className="px-1 py-0.5 border border-gray-300 rounded text-[10px]"
            >
              <option value="all">All</option>
              <option value="[0]">Step 0 only</option>
              <option value="[1]">Step 1 only</option>
              <option value="[0,1]">Steps 0-1</option>
            </select>
          </div>
        )}
        {setLastOccurrenceOnly && (
          <label className="flex items-center gap-1 text-[10px] text-gray-400 ml-2" title="Keep only the last target-word occurrence per prompt">
            <input
              type="checkbox"
              checked={!!lastOccurrenceOnly}
              onChange={e => setLastOccurrenceOnly(e.target.checked)}
            />
            Last only
          </label>
        )}
        {setMaxProbes && (
          <label
            className="flex items-center gap-1 text-[10px] text-gray-400 ml-2"
            title="Cap total probes before clustering, expert routes, and UMAP run. Takes effect on next Run."
          >
            <span>Samples</span>
            <input
              type="range"
              min={1}
              max={filteredProbeCount || 1000}
              step={1}
              value={maxProbes ?? filteredProbeCount ?? 1000}
              onChange={e => setMaxProbes(Number(e.target.value))}
              className="w-20"
            />
            <span className="w-10 text-right tabular-nums">
              {maxProbes ?? filteredProbeCount ?? '—'}
            </span>
            {maxProbes != null && (
              <button
                type="button"
                onClick={() => setMaxProbes(null)}
                className="text-gray-400 hover:text-gray-600"
                title="Clear cap"
              >×</button>
            )}
          </label>
        )}
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
            steps={steps}
            lastOccurrenceOnly={lastOccurrenceOnly}
            maxProbes={maxProbes}
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
            manualTrigger={true}
            onAnalysisReady={handleTrajectoryAnalysisReady}
            steps={steps}
            lastOccurrenceOnly={lastOccurrenceOnly}
            maxProbes={maxProbes}
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
