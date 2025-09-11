import React, { useState, useEffect, useCallback } from 'react'
import SankeyChart from './SankeyChart'
import type { RouteAnalysisResponse, ClusteringConfig } from '../../types/api'
import type { ColorAxis, GradientScheme } from '../../utils/colorBlending'
import type { FilterState } from '../WordFilterPanel'
import { apiClient } from '../../api/client'
import { LAYER_RANGES } from '../../constants/layerRanges'

interface MultiSankeyViewProps {
  sessionId: string
  sessionData: any
  filterState: FilterState
  primaryAxis: ColorAxis
  secondaryAxis?: ColorAxis
  primaryGradient?: GradientScheme
  secondaryGradient?: GradientScheme
  showAllRoutes: boolean
  topRoutes: number
  selectedRange?: string
  onRangeChange?: (range: string) => void
  onNodeClick?: (nodeData: any) => void
  onLinkClick?: (linkData: any) => void
  onRouteDataLoaded?: (routeDataMap: Record<string, RouteAnalysisResponse | null>) => void
  // Clustering mode support
  mode?: 'expert' | 'cluster'
  clusteringConfig?: ClusteringConfig
  manualTrigger?: boolean  // If true, only loads when runAnalysis is called externally
  onAnalysisReady?: (runAnalysis: () => void) => void  // Callback to provide runAnalysis function to parent
}


export default function MultiSankeyView({
  sessionId,
  sessionData,
  filterState,
  primaryAxis,
  secondaryAxis,
  primaryGradient,
  secondaryGradient,
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

  // Loading function that can be called manually or automatically
  const loadAllWindows = useCallback(async () => {
    if (!sessionId || !sessionData || !currentRange) {
      setRouteDataMap({})
      return
    }
    const newLoadingMap: Record<string, boolean> = {}
    const newRouteDataMap: Record<string, RouteAnalysisResponse | null> = {}
    const newErrorMap: Record<string, string | null> = {}

    // Set all to loading
    currentRange.windows.forEach(window => {
      newLoadingMap[window.id] = true
    })
    setLoadingMap(newLoadingMap)

    // Load each window in parallel
    const promises = currentRange.windows.map(async (window) => {
      try {
        const filterConfig = convertFilterState(filterState, sessionData)
        const request = {
          session_id: sessionId,
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
    
    // Notify parent that route data is loaded
    onRouteDataLoaded?.(newRouteDataMap)
  }, [sessionId, sessionData, selectedRange, filterState, showAllRoutes, topRoutes, mode, clusteringConfig, onRouteDataLoaded])

  // Provide the loading function to parent via callback
  React.useEffect(() => {
    if (onAnalysisReady) {
      onAnalysisReady(loadAllWindows)
    }
  }, [onAnalysisReady, loadAllWindows])

  // Auto-load data for expert mode or when manual trigger is disabled
  useEffect(() => {
    // Skip auto-loading if manual trigger is enabled
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
                    primaryAxis={primaryAxis}
                    secondaryAxis={secondaryAxis}
                    primaryGradient={primaryGradient}
                    secondaryGradient={secondaryGradient}
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
                        
                        // Add mode-specific fields
                        if (mode === 'cluster') {
                          enrichedData.clusterId = nodeData.expert_id // Backend uses expert_id field for cluster ID
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

// Helper function - copy from ExperimentPage
function convertFilterState(filterState: FilterState, sessionData: any): any {
  const filterConfig: any = {}
  
  if (filterState.contextCategories.size > 0) {
    filterConfig.context_categories = Array.from(filterState.contextCategories)
  }
  if (filterState.targetCategories.size > 0) {
    filterConfig.target_categories = Array.from(filterState.targetCategories)
  }

  // Apply balanced sampling if enabled
  if (filterState.balanceCategories && sessionData) {
    const sampledWords = applyBalancedSampling(sessionData, filterState)
    if (sampledWords.contextWords) {
      filterConfig.context_words = sampledWords.contextWords
    }
    if (sampledWords.targetWords) {
      filterConfig.target_words = sampledWords.targetWords
    }
    filterConfig.max_per_category = filterState.maxWordsPerCategory
  }

  return Object.keys(filterConfig).length > 0 ? filterConfig : undefined
}

// Copy balanced sampling function from ExperimentPage
function applyBalancedSampling(sessionData: any, filterState: FilterState): { contextWords?: string[], targetWords?: string[] } {
  if (!sessionData?.categories) return {}

  const sampleWordsFromCategory = (words: string[], maxCount: number): string[] => {
    if (words.length <= maxCount) return [...words]
    
    const shuffled = [...words]
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
    }
    return shuffled.slice(0, maxCount)
  }

  const result: { contextWords?: string[], targetWords?: string[] } = {}

  // Sample context words
  if (filterState.contextCategories.size > 0) {
    const contextWords: string[] = []
    for (const category of filterState.contextCategories) {
      // Find words that have this category
      const wordsInCategory = Object.keys(sessionData.categories.contexts || {})
        .filter(word => sessionData.categories.contexts[word].includes(category))
      const sampled = sampleWordsFromCategory(wordsInCategory, filterState.maxWordsPerCategory)
      contextWords.push(...sampled)
    }
    result.contextWords = contextWords
  }

  // Sample target words
  if (filterState.targetCategories.size > 0) {
    const targetWords: string[] = []
    for (const category of filterState.targetCategories) {
      // Find words that have this category
      const wordsInCategory = Object.keys(sessionData.categories.targets || {})
        .filter(word => sessionData.categories.targets[word].includes(category))
      const sampled = sampleWordsFromCategory(wordsInCategory, filterState.maxWordsPerCategory)
      targetWords.push(...sampled)
    }
    result.targetWords = targetWords
  }

  return result
}