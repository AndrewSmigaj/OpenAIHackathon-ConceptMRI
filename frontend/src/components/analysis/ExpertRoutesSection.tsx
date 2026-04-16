import { useState, useCallback } from 'react'
import type { SessionDetailResponse, RouteAnalysisResponse } from '../../types/api'
import type { FilterState } from '../WordFilterPanel'
import type { GradientScheme } from '../../utils/colorBlending'
import type { SelectedCard } from '../../types/analysis'
import MultiSankeyView from '../charts/MultiSankeyView'


interface ExpertRoutesSectionProps {
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
  clusteringSchema?: string
  steps?: number[] | null
  lastOccurrenceOnly?: boolean
  maxProbes?: number | null
  topRoutes: number
  selectedRange: string
  onRangeChange: (range: string) => void
  showAllRoutes: boolean
  onRouteDataLoaded: (routeDataMap: Record<string, RouteAnalysisResponse | null>) => void
  onCardSelect: (card: SelectedCard) => void
}

export default function ExpertRoutesSection({
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
  clusteringSchema,
  steps,
  lastOccurrenceOnly,
  maxProbes,
  topRoutes,
  selectedRange,
  onRangeChange,
  showAllRoutes,
  onRouteDataLoaded,
  onCardSelect
}: ExpertRoutesSectionProps) {
  const [runAnalysis, setRunAnalysis] = useState<(() => void) | null>(null)
  const [expertRank, setExpertRank] = useState<number>(1)

  const handleSankeyClick = (elementType: 'expert' | 'route', data: any) => {
    onCardSelect({
      type: elementType === 'expert' ? 'expert' : 'highway',
      data
    })
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-1">
      <div className="flex items-center gap-2 mb-1 px-1">
        <span className="text-xs font-semibold text-gray-900">Expert Routes</span>
        <button
          onClick={() => runAnalysis?.()}
          disabled={!runAnalysis}
          className="px-2 py-0.5 bg-blue-600 text-white text-[10px] font-medium rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          Run
        </button>
        <label className="text-[10px] text-gray-600 flex items-center gap-1">
          Rank
          <select
            value={expertRank}
            onChange={(e) => setExpertRank(Number(e.target.value))}
            className="px-1 py-0.5 border border-gray-300 rounded text-[10px] focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value={1}>1</option>
            <option value={2}>2</option>
            <option value={3}>3</option>
          </select>
        </label>
      </div>

      <div className="bg-gray-50 rounded-lg p-1">
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
          clusteringSchema={clusteringSchema}
          steps={steps}
          lastOccurrenceOnly={lastOccurrenceOnly}
          maxProbes={maxProbes}
          expertRank={expertRank}
          showAllRoutes={showAllRoutes}
          topRoutes={topRoutes}
          selectedRange={selectedRange}
          onRangeChange={onRangeChange}
          onNodeClick={(data) => handleSankeyClick('expert', data)}
          onLinkClick={(data) => handleSankeyClick('route', data)}
          onRouteDataLoaded={onRouteDataLoaded}
          mode="expert"
          manualTrigger={true}
          onAnalysisReady={useCallback((analysisFunction) => setRunAnalysis(() => analysisFunction), [])}
        />
      </div>
    </div>
  )
}
