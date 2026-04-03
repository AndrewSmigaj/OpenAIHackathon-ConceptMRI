import React, { useState, useEffect, useCallback } from 'react'
import SankeyChart from './SankeyChart'
import type { RouteAnalysisResponse, ClusteringConfig } from '../../types/api'
import type { GradientScheme } from '../../utils/colorBlending'
import type { FilterState } from '../WordFilterPanel'
import { apiClient } from '../../api/client'
import { LAYER_RANGES } from '../../constants/layerRanges'
import { isOutputNode, isOutputLink } from '../../constants/outputNodes'

interface MultiSankeyViewProps {
  sessionIds: string[]
  sessionData: any
  filterState: FilterState
  primaryValues: string[]
  gradient?: GradientScheme
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
  showAllRoutes: boolean
  topRoutes: number
  selectedRange?: string
  onRangeChange?: (range: string) => void
  onNodeClick?: (nodeData: any) => void
  onLinkClick?: (linkData: any) => void
  onRouteDataLoaded?: (routeDataMap: Record<string, RouteAnalysisResponse | null>) => void
  mode?: 'expert' | 'cluster'
  clusteringConfig?: ClusteringConfig
  clusteringSchema?: string
  manualTrigger?: boolean
  onAnalysisReady?: (runAnalysis: () => void) => void
}


export default function MultiSankeyView({
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
  showAllRoutes,
  topRoutes,
  selectedRange = 'range1',
  onRangeChange,
  onNodeClick,
  onLinkClick,
  onRouteDataLoaded,
  mode = 'expert',
  clusteringConfig,
  clusteringSchema,
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
          top_n_routes: showAllRoutes ? 1000 : topRoutes,
          ...(outputGroupingAxes ? { output_grouping_axes: outputGroupingAxes } : {}),
        }
        const response = mode === 'cluster' && clusteringConfig
          ? await apiClient.analyzeClusterRoutes({
              ...request,
              clustering_config: clusteringConfig,
              ...(clusteringSchema ? { clustering_schema: clusteringSchema } : {})
            })
          : await apiClient.analyzeRoutes({
              ...request,
              ...(clusteringSchema ? { clustering_schema: clusteringSchema } : {})
            })
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
  }, [sessionIds, sessionData, selectedRange, filterState, showAllRoutes, topRoutes, mode, clusteringConfig, clusteringSchema, outputGroupingAxes, onRouteDataLoaded])

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
    <div className="space-y-1">
      {/* Compact layer range selector */}
      <div className="flex items-center gap-2">
        <select
          value={selectedRange}
          onChange={(e) => onRangeChange?.(e.target.value)}
          className="px-1.5 py-0.5 border border-gray-300 rounded text-[10px] focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {Object.entries(LAYER_RANGES).map(([key, range]) => (
            <option key={key} value={key}>
              {range.label}
            </option>
          ))}
        </select>
        {currentRange.windows.map(w => (
          <span key={w.id} className="text-[9px] text-gray-400">{w.label}</span>
        ))}
      </div>

      {/* 6 Sankey Charts + Output Chart */}
      <div className="flex gap-0">
        {/* 6 layer windows */}
        <div className="flex-1 grid grid-cols-6 gap-0">
        {currentRange.windows.map((window) => {
          const routeData = routeDataMap[window.id]
          const loading = loadingMap[window.id]
          const error = errorMap[window.id]

          return (
            <div key={window.id} className="bg-white">
              <div className="p-0" style={{ height: '200px' }}>
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
                    nodes={routeData.nodes.filter(n => !isOutputNode(n.name))}
                    links={routeData.links.filter(l => !isOutputLink(l))}
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
                    height={195}
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

        {/* 7th chart: output category mapping from last window */}
        {(() => {
          const lastWindow = currentRange.windows[currentRange.windows.length - 1]
          const lastData = routeDataMap[lastWindow?.id]
          if (!lastData) return null
          const outputNodes = lastData.nodes.filter(n => isOutputNode(n.name))
          if (outputNodes.length === 0) return null
          // Get final-layer nodes that link to output nodes
          const outputLinks = lastData.links.filter(l => isOutputLink(l))
          const sourceNames = new Set(outputLinks.map(l => l.source))
          const sourceNodes = lastData.nodes.filter(n => sourceNames.has(n.name))
          return (
            <div className="bg-white flex-shrink-0" style={{ width: '120px' }}>
              <div className="p-0" style={{ height: '200px' }}>
                <SankeyChart
                  nodes={[...sourceNodes, ...outputNodes]}
                  links={outputLinks}
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
                  nodeWidth={14}
                  onNodeClick={(nodeId, nodeData) => {
                    if (onNodeClick) {
                      onNodeClick({
                        ...nodeData,
                        population: nodeData.token_count,
                        coverage: Math.round((nodeData.token_count / lastData.statistics.total_probes) * 100),
                        _fullData: nodeData,
                        _totalProbes: lastData.statistics.total_probes,
                        _window: lastWindow.label
                      })
                    }
                  }}
                  onLinkClick={(linkData) => {
                    if (onLinkClick) {
                      onLinkClick({
                        ...linkData,
                        signature: linkData.route_signature,
                        flow: linkData.value,
                        coverage: Math.round((linkData.value / lastData.statistics.total_probes) * 100),
                        _fullData: linkData,
                        _totalProbes: lastData.statistics.total_probes,
                        _window: lastWindow.label
                      })
                    }
                  }}
                  height={195}
                />
              </div>
            </div>
          )
        })()}
      </div>
    </div>
  )
}

import { convertFilterState } from '../../utils/filterState'
