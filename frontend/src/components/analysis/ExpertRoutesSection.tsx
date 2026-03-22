import { useState, useCallback } from 'react'
import type { SessionDetailResponse, RouteAnalysisResponse } from '../../types/api'
import type { FilterState } from '../WordFilterPanel'
import type { GradientScheme } from '../../utils/colorBlending'
import type { SelectedCard } from '../../types/analysis'
import MultiSankeyView from '../charts/MultiSankeyView'
import { ChartBarIcon } from '../icons/Icons'

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
    <div className="bg-white rounded-xl shadow-sm p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Expert Routing Pathways</h3>
          <p className="text-xs text-gray-600 mt-1">Click experts or routes to see details</p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => runAnalysis?.()}
            disabled={!runAnalysis}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Run Analysis
          </button>
          <ChartBarIcon style={{ width: '12px', height: '12px' }} className="text-blue-600" />
        </div>
      </div>

      {/* Multi-Sankey Route Analysis Visualization */}
      <div className="bg-gray-50 rounded-lg p-6">
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
