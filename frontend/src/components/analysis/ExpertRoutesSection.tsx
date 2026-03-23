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
  colorLabelA: string
  colorLabelB: string
  gradient: GradientScheme
  secondaryCategoryA?: string
  secondaryCategoryB?: string
  secondaryGradient?: GradientScheme
  secondaryAxisId?: string
  outputColorLabelA?: string
  outputColorLabelB?: string
  outputGradient?: GradientScheme
  outputSecondaryCategoryA?: string
  outputSecondaryCategoryB?: string
  outputSecondaryGradient?: GradientScheme
  outputSecondaryAxisId?: string
  outputColorAxisId?: string
  outputGroupingAxes?: string[]
  clusteringSchema?: string
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
  colorLabelA,
  colorLabelB,
  gradient,
  secondaryCategoryA,
  secondaryCategoryB,
  secondaryGradient,
  secondaryAxisId,
  outputColorLabelA,
  outputColorLabelB,
  outputGradient,
  outputSecondaryCategoryA,
  outputSecondaryCategoryB,
  outputSecondaryGradient,
  outputSecondaryAxisId,
  outputColorAxisId,
  outputGroupingAxes,
  clusteringSchema,
  topRoutes,
  selectedRange,
  onRangeChange,
  showAllRoutes,
  onRouteDataLoaded,
  onCardSelect
}: ExpertRoutesSectionProps) {
  const [runAnalysis, setRunAnalysis] = useState<(() => void) | null>(null)

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
      </div>

      <div className="bg-gray-50 rounded-lg p-1">
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
          outputColorLabelA={outputColorLabelA}
          outputColorLabelB={outputColorLabelB}
          outputGradient={outputGradient}
          outputSecondaryCategoryA={outputSecondaryCategoryA}
          outputSecondaryCategoryB={outputSecondaryCategoryB}
          outputSecondaryGradient={outputSecondaryGradient}
          outputSecondaryAxisId={outputSecondaryAxisId}
          outputColorAxisId={outputColorAxisId}
          outputGroupingAxes={outputGroupingAxes}
          clusteringSchema={clusteringSchema}
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
