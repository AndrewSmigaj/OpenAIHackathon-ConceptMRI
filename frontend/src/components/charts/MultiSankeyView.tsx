import React, { useState, useEffect, useCallback } from 'react'
import SankeyChart from './SankeyChart'
import type { RouteAnalysisResponse, ClusteringConfig } from '../../types/api'
import type { GradientScheme } from '../../utils/colorBlending'
import type { FilterState } from '../WordFilterPanel'
import { apiClient } from '../../api/client'
import { LAYER_RANGES } from '../../constants/layerRanges'

interface MultiSankeyViewProps {
  sessionIds: string[]
  sessionData: any
  filterState: FilterState
  colorLabelA: string
  colorLabelB: string
  gradient?: GradientScheme
  showAllRoutes: boolean
  topRoutes: number
  selectedRange?: string
  onRangeChange?: (range: string) => void
  onNodeClick?: (nodeData: any) => void
  onLinkClick?: (linkData: any) => void
  onRouteDataLoaded?: (routeDataMap: Record<string, RouteAnalysisResponse | null>) => void
  mode?: 'expert' | 'cluster'
  clusteringConfig?: ClusteringConfig
  manualTrigger?: boolean
  onAnalysisReady?: (runAnalysis: () => void) => void
}


export default function MultiSankeyView({
  sessionIds,
  sessionData,
  filterState,
  colorLabelA,
  colorLabelB,
  gradient,
  showAllRoutes,
  topRoutes,
  selectedRange = 'range1',
  onRangeChange,
  onNodeClick,
  onLinkClick,
  onRouteDataLoaded,
  mode = 'expert',
  clusteringConfig,
  manualTrigger = false,
  onAnalysisReady
}: MultiSankeyViewProps) {
  const [routeDataMap, setRouteDataMap] = useState<Record<string, RouteAnalysisResponse | null>>({})
  const [loadingMap, setLoadingMap] = useState<Record<string, boolean>>({})
  const [errorMap, setErrorMap] = useState<Record<string, string | null>>({})

  const currentRange = LAYER_RANGES[selectedRange as keyof typeof LAYER_RANGES]

  const loadAllWindows = useCallback(async () => {
    if (!sessionIds || sessionIds.length === 0 || !sessionData || !currentRange) {
      setRouteDataMap({})
      return
    }
    const newLoadingMap: Record<string, boolean> = {}
    const newRouteDataMap: Record<string, RouteAnalysisResponse | null> = {}
    const newErrorMap: Record<string, string | null> = {}

    currentRange.windows.forEach(window => {
      newLoadingMap[window.id] = true
    })
    setLoadingMap(newLoadingMap)

    const promises = currentRange.windows.map(async (window) => {
      try {
        const filterConfig = convertFilterState(filterState)
        const request = {
          session_ids: sessionIds,
          window_layers: window.layers,
          filter_config: filterConfig,
          top_n_routes: showAllRoutes ? 1000 : topRoutes
        }
        const response = mode === 'cluster' && clusteringConfig
          ? await apiClient.analyzeClusterRoutes({
              ...request,
              clustering_config: clusteringConfig
            })
          : await apiClient.analyzeRoutes(request)
        newRouteDataMap[window.id] = response
        newErrorMap[window.id] = null
      } catch (err) {
        console.error(`Failed to load routes for ${window.id}:`, err)
        newErrorMap[window.id] = err instanceof Error ? err.message : 'Failed to load'
        newRouteDataMap[window.id] = null
      } finally {
        newLoadingMap[window.id] = false
      }
    })

    await Promise.all(promises)

    setRouteDataMap(newRouteDataMap)
    setErrorMap(newErrorMap)
    setLoadingMap(newLoadingMap)

    onRouteDataLoaded?.(newRouteDataMap)
  }, [sessionIds, sessionData, selectedRange, filterState, showAllRoutes, topRoutes, mode, clusteringConfig, onRouteDataLoaded])

  React.useEffect(() => {
    if (onAnalysisReady) {
      onAnalysisReady(loadAllWindows)
    }
  }, [onAnalysisReady, loadAllWindows])

  useEffect(() => {
    if (manualTrigger) {
      return
    }

    loadAllWindows()
  }, [loadAllWindows, manualTrigger])

  return (
    <div className="space-y-4">
      {/* Range Selector */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h3 className="text-lg font-semibold text-gray-900">Multi-Layer Analysis</h3>
          <select
            value={selectedRange}
            onChange={(e) => onRangeChange?.(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {Object.entries(LAYER_RANGES).map(([key, range]) => (
              <option key={key} value={key}>
                {range.label}
              </option>
            ))}
          </select>
        </div>
        <p className="text-sm text-gray-500">
          Showing 6 consecutive layer transitions
        </p>
      </div>

      {/* 6 Sankey Charts in a Row */}
      <div className="grid grid-cols-6 gap-3">
        {currentRange.windows.map((window) => {
          const routeData = routeDataMap[window.id]
          const loading = loadingMap[window.id]
          const error = errorMap[window.id]

          return (
            <div key={window.id} className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="px-2 py-1.5 border-b border-gray-200 bg-gray-50">
                <h4 className="text-xs font-semibold text-gray-900 text-center">{window.label}</h4>
                {routeData && (
                  <p className="text-xs text-gray-500 text-center mt-0.5">
                    {routeData.statistics.total_routes}r • {routeData.statistics.total_probes}t
                  </p>
                )}
              </div>

              <div className="p-1" style={{ height: '280px' }}>
                {loading ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-1"></div>
                      <p className="text-xs text-gray-600">Loading...</p>
                    </div>
                  </div>
                ) : error ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <p className="text-xs text-red-600">Error</p>
                    </div>
                  </div>
                ) : routeData ? (
                  <SankeyChart
                    nodes={routeData.nodes}
                    links={routeData.links}
                    colorLabelA={colorLabelA}
                    colorLabelB={colorLabelB}
                    gradient={gradient}
                    onNodeClick={(nodeId, nodeData) => {
                      if (onNodeClick) {
                        const enrichedData = {
                          ...nodeData,
                          population: nodeData.token_count,
                          coverage: Math.round((nodeData.token_count / routeData.statistics.total_probes) * 100),
                          _fullData: nodeData,
                          _totalProbes: routeData.statistics.total_probes,
                          _window: window.label
                        }

                        if (mode === 'cluster') {
                          enrichedData.clusterId = nodeData.expert_id
                        } else {
                          enrichedData.expertId = nodeData.expert_id
                        }

                        onNodeClick(enrichedData)
                      }
                    }}
                    onLinkClick={(linkData) => {
                      if (onLinkClick) {
                        const routeInfo = routeData.top_routes.find(r => r.signature === linkData.route_signature)
                        onLinkClick({
                          ...linkData,
                          ...(routeInfo || {}),
                          signature: linkData.route_signature,
                          flow: linkData.value,
                          coverage: Math.round((linkData.value / routeData.statistics.total_probes) * 100),
                          _fullData: linkData,
                          _routeInfo: routeInfo,
                          _totalProbes: routeData.statistics.total_probes,
                          _window: window.label
                        })
                      }
                    }}
                    width={150}
                    height={220}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-xs text-gray-400">No data</p>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Convert FilterState to API FilterConfig
function convertFilterState(filterState: FilterState): any {
  const filterConfig: any = {}

  if (filterState.labels?.size > 0) {
    filterConfig.labels = Array.from(filterState.labels)
  }

  return Object.keys(filterConfig).length > 0 ? filterConfig : undefined
}
