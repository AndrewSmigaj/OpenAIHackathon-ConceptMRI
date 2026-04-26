import React, { useState, useEffect, useCallback } from 'react'
import SankeyChart from './SankeyChart'
import type { RouteAnalysisResponse } from '../../types/api'
import type { GradientScheme, AmbiguityBlend } from '../../utils/colorBlending'
import { apiClient } from '../../api/client'
import { LAYER_WINDOWS } from '../../constants/layerWindows'
import { isOutputNode, isOutputLink } from '../../constants/outputNodes'

interface MultiSankeyViewProps {
  sessionIds: string[]
  sessionData: any
  schemaName: string
  primaryValues: string[]
  gradient?: GradientScheme
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
  showAllRoutes: boolean
  topRoutes: number
  selectedWindow?: string
  onWindowChange?: (windowId: string) => void
  onNodeClick?: (nodeData: any) => void
  onLinkClick?: (linkData: any) => void
  onRouteDataLoaded?: (routeDataMap: Record<string, RouteAnalysisResponse | null>) => void
  mode?: 'expert' | 'cluster'
  expertRank?: number | null
  manualTrigger?: boolean
  onAnalysisReady?: (runAnalysis: () => void) => void
}


export default function MultiSankeyView({
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
  showAllRoutes,
  topRoutes,
  selectedWindow = 'w0',
  onWindowChange,
  onNodeClick,
  onLinkClick,
  onRouteDataLoaded,
  mode = 'expert',
  expertRank,
  manualTrigger = false,
  onAnalysisReady
}: MultiSankeyViewProps) {
  const [routeDataMap, setRouteDataMap] = useState<Record<string, RouteAnalysisResponse | null>>({})
  const [loadingMap, setLoadingMap] = useState<Record<string, boolean>>({})
  const [errorMap, setErrorMap] = useState<Record<string, string | null>>({})

  const currentWindow = LAYER_WINDOWS[selectedWindow as keyof typeof LAYER_WINDOWS]

  const loadAllTransitions = useCallback(async () => {
    if (!sessionIds || sessionIds.length === 0 || !sessionData || !currentWindow || !schemaName) {
      setRouteDataMap({})
      return
    }
    const newLoadingMap: Record<string, boolean> = {}
    const newRouteDataMap: Record<string, RouteAnalysisResponse | null> = {}
    const newErrorMap: Record<string, string | null> = {}

    currentWindow.transitions.forEach(transition => {
      newLoadingMap[transition.id] = true
    })
    setLoadingMap(newLoadingMap)

    const promises = currentWindow.transitions.map(async (transition) => {
      try {
        const baseRequest = {
          session_ids: sessionIds,
          schema_name: schemaName,
          transition_layers: transition.layers,
          top_n_routes: showAllRoutes ? 1000 : topRoutes,
          ...(outputGroupingAxes ? { output_grouping_axes: outputGroupingAxes } : {}),
        }
        const response = mode === 'cluster'
          ? await apiClient.analyzeClusterRoutes(baseRequest)
          : await apiClient.analyzeRoutes({
              ...baseRequest,
              ...(expertRank ? { expert_rank: expertRank } : {})
            })
        newRouteDataMap[transition.id] = response
        newErrorMap[transition.id] = null
      } catch (err) {
        console.error(`Failed to load routes for ${transition.id}:`, err)
        newErrorMap[transition.id] = err instanceof Error ? err.message : 'Failed to load'
        newRouteDataMap[transition.id] = null
      } finally {
        newLoadingMap[transition.id] = false
      }
    })

    await Promise.all(promises)

    // --- Barycenter cross-transition node ordering (forward sweep L→R) ---
    // Propagate vertical positions across transitions so the same cluster
    // keeps consistent placement, minimizing link crossings.
    let prevRightOrder: Map<string, number> | null = null

    for (const transition of currentWindow.transitions) {
      const data = newRouteDataMap[transition.id]
      if (!data) {
        prevRightOrder = null
        continue
      }

      const leftLayer = Math.min(...transition.layers)
      const rightLayer = Math.max(...transition.layers)

      const getLayer = (name: string): number | null => {
        const m = name.match(/^L(\d+)\//)
        return m ? parseInt(m[1], 10) : null
      }

      const leftNodes: typeof data.nodes = []
      const rightNodes: typeof data.nodes = []
      const otherNodes: typeof data.nodes = []

      for (const node of data.nodes) {
        const layer = getLayer(node.name)
        if (layer === leftLayer) leftNodes.push(node)
        else if (layer === rightLayer) rightNodes.push(node)
        else otherNodes.push(node)
      }

      // Left column: inherit previous transition's right ordering, or sort by size
      if (prevRightOrder && prevRightOrder.size > 0) {
        leftNodes.sort((a, b) =>
          (prevRightOrder!.get(a.name) ?? Infinity) - (prevRightOrder!.get(b.name) ?? Infinity)
        )
      } else {
        leftNodes.sort((a, b) => (b.token_count || 0) - (a.token_count || 0))
      }

      // Build left position index
      const leftPos = new Map<string, number>()
      leftNodes.forEach((n, i) => leftPos.set(n.name, i))

      // Compute barycenter for each right node
      const bary = new Map<string, number>()
      for (const node of rightNodes) {
        let wSum = 0, wTotal = 0
        for (const link of data.links) {
          if (link.target === node.name && leftPos.has(link.source)) {
            wSum += link.value * leftPos.get(link.source)!
            wTotal += link.value
          }
        }
        bary.set(node.name, wTotal > 0 ? wSum / wTotal : Infinity)
      }

      // Sort right column by barycenter
      rightNodes.sort((a, b) => (bary.get(a.name) ?? Infinity) - (bary.get(b.name) ?? Infinity))

      // Store right order for next transition's left column
      prevRightOrder = new Map()
      rightNodes.forEach((n, i) => prevRightOrder!.set(n.name, i))

      // Reassemble nodes in sorted order
      data.nodes = [...leftNodes, ...rightNodes, ...otherNodes]
    }

    setRouteDataMap(newRouteDataMap)
    setErrorMap(newErrorMap)
    setLoadingMap(newLoadingMap)

    onRouteDataLoaded?.(newRouteDataMap)
  }, [sessionIds, sessionData, selectedWindow, schemaName, showAllRoutes, topRoutes, mode, outputGroupingAxes, expertRank, onRouteDataLoaded])

  React.useEffect(() => {
    if (onAnalysisReady) {
      onAnalysisReady(loadAllTransitions)
    }
  }, [onAnalysisReady, loadAllTransitions])

  useEffect(() => {
    if (manualTrigger) {
      return
    }

    loadAllTransitions()
  }, [loadAllTransitions, manualTrigger])

  return (
    <div className="space-y-1">
      {/* Compact window selector */}
      <div className="flex items-center gap-2">
        <select
          value={selectedWindow}
          onChange={(e) => onWindowChange?.(e.target.value)}
          className="px-1.5 py-0.5 border border-gray-300 rounded text-[10px] focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {Object.entries(LAYER_WINDOWS).map(([key, window]) => (
            <option key={key} value={key}>
              {window.label}
            </option>
          ))}
        </select>
        {currentWindow.transitions.map(t => (
          <span key={t.id} className="text-[9px] text-gray-400">{t.label}</span>
        ))}
      </div>

      {/* 6 Sankey Charts + Output Chart */}
      <div className="flex gap-0">
        {/* 6 layer transitions */}
        <div className="flex-1 grid grid-cols-6 gap-0">
        {currentWindow.transitions.map((transition) => {
          const routeData = routeDataMap[transition.id]
          const loading = loadingMap[transition.id]
          const error = errorMap[transition.id]

          return (
            <div key={transition.id} className="bg-white">
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
                    ambiguityBlend={ambiguityBlend}
                    outputPrimaryValues={outputPrimaryValues}
                    outputGradient={outputGradient}
                    outputSecondaryValues={outputSecondaryValues}
                    outputSecondaryGradient={outputSecondaryGradient}
                    outputSecondaryAxisId={outputSecondaryAxisId}
                    outputColorAxisId={outputColorAxisId}
                    onNodeClick={(_nodeId, nodeData) => {
                      if (onNodeClick) {
                        const enrichedData: any = {
                          ...nodeData,
                          population: nodeData.token_count,
                          coverage: Math.round((nodeData.token_count / routeData.statistics.total_probes) * 100),
                          _fullData: nodeData,
                          _totalProbes: routeData.statistics.total_probes,
                          _window: transition.label
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
                          _window: transition.label
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

        {/* 7th chart: output category mapping from last transition */}
        {(() => {
          const lastTransition = currentWindow.transitions[currentWindow.transitions.length - 1]
          const lastData = routeDataMap[lastTransition?.id]
          if (!lastData) return null
          const outputNodes = lastData.nodes.filter(n => isOutputNode(n.name))
          if (outputNodes.length === 0) return null
          // Get final-layer nodes that link to output nodes
          const outputLinks = lastData.links.filter(l => isOutputLink(l))
          const sourceNames = new Set(outputLinks.map(l => l.source))
          const sourceNodes = lastData.nodes.filter(n => sourceNames.has(n.name))
          return (
            <div className="bg-white flex-shrink-0" style={{ width: '240px' }}>
              <div className="p-0" style={{ height: '200px' }}>
                <SankeyChart
                  nodes={[...sourceNodes, ...outputNodes]}
                  links={outputLinks}
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
                  nodeWidth={14}
                  onNodeClick={(_nodeId, nodeData) => {
                    if (onNodeClick) {
                      onNodeClick({
                        ...nodeData,
                        population: nodeData.token_count,
                        coverage: Math.round((nodeData.token_count / lastData.statistics.total_probes) * 100),
                        _fullData: nodeData,
                        _totalProbes: lastData.statistics.total_probes,
                        _window: lastTransition.label
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
                        _window: lastTransition.label
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
