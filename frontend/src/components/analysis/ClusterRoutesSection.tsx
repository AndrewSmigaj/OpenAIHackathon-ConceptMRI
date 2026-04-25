import { useCallback, useMemo } from 'react'
import type { SessionDetailResponse, RouteAnalysisResponse } from '../../types/api'
import type { GradientScheme, AmbiguityBlend } from '../../utils/colorBlending'
import type { SelectedCard } from '../../types/analysis'
import type { DynamicAxis } from '../../types/api'
import MultiSankeyView from '../charts/MultiSankeyView'
import SteppedTrajectoryPlot from '../charts/SteppedTrajectoryPlot'

import { LAYER_RANGES } from '../../constants/layerRanges'

interface ClusterRoutesSectionProps {
  sessionIds: string[]
  sessionData: SessionDetailResponse | null
  schemaName: string
  primaryValues: string[]
  gradient: GradientScheme
  secondaryValues?: string[]
  secondaryGradient?: GradientScheme
  secondaryAxisId?: string
  ambiguityBlend?: AmbiguityBlend
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
  maxTrajectories?: number
  trajectoryTitle?: string
  onRouteDataLoaded?: (routeDataMap: Record<string, RouteAnalysisResponse | null>) => void
  onCardSelect: (card: SelectedCard) => void
  onSankeyAnalysisReady?: (fn: () => void) => void
  onTrajectoryAnalysisReady?: (fn: () => void) => void
  selectedProbeId?: string | null
}

export default function ClusterRoutesSection({
  sessionIds,
  sessionData,
  schemaName,
  primaryValues,
  gradient,
  secondaryValues,
  secondaryGradient,
  secondaryAxisId,
  ambiguityBlend,
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
  maxTrajectories,
  trajectoryTitle,
  onRouteDataLoaded,
  onCardSelect,
  onSankeyAnalysisReady,
  onTrajectoryAnalysisReady,
  selectedProbeId
}: ClusterRoutesSectionProps) {
  const memoizedLayers = useMemo(() => {
    return LAYER_RANGES[selectedRange as keyof typeof LAYER_RANGES]?.windows.map(w => w.layers).flat() || []
  }, [selectedRange])

  const handleVisualizationClick = useCallback((elementType: 'cluster' | 'trajectory', data: any) => {
    onCardSelect({
      type: elementType === 'cluster' ? 'cluster' : 'route',
      data
    })
  }, [onCardSelect])

  const onTrajectoryPointClick = useCallback((info: { probe_id: string; target: string; label?: string }) => {
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
        } as any
      })
    }
  }, [sessionData, onCardSelect])

  const sessionId = sessionIds[0]

  return (
    <div className="bg-white rounded-xl shadow-sm p-1">
      <div className="flex items-center gap-2 mb-1 px-1">
        <span className="text-xs font-semibold text-gray-900">Clusters & Routes</span>
      </div>

      <div>
        <div className="bg-gray-50 rounded-lg p-1 mb-2">
          <MultiSankeyView
            sessionIds={sessionIds}
            sessionData={sessionData}
            schemaName={schemaName}
            primaryValues={primaryValues}
            gradient={gradient}
            secondaryValues={secondaryValues}
            secondaryGradient={secondaryGradient}
            secondaryAxisId={secondaryAxisId}
            ambiguityBlend={ambiguityBlend}
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
            onAnalysisReady={onSankeyAnalysisReady}
          />
        </div>

        {sessionId && schemaName && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <SteppedTrajectoryPlot
              sessionId={sessionId}
              schemaName={schemaName}
              layers={memoizedLayers}
              title={trajectoryTitle}
              colorLabelA={primaryValues[0] || ''}
              colorLabelB={primaryValues[1] || ''}
              gradient={gradient}
              primaryValues={primaryValues}
              secondaryColorAxisId={secondaryAxisId}
              secondaryValues={secondaryValues}
              shapeAxisId={shapeAxisId}
              shapeValues={shapeAxis?.values}
              ambiguityBlend={ambiguityBlend}
              height={400}
              manualTrigger={true}
              onAnalysisReady={onTrajectoryAnalysisReady}
              maxTrajectories={maxTrajectories}
              selectedProbeId={selectedProbeId}
              onPointClick={onTrajectoryPointClick}
            />
          </div>
        )}
      </div>
    </div>
  )
}
