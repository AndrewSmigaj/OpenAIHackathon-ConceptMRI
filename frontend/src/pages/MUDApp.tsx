import { useState, useEffect, useCallback, useMemo } from 'react'
import type {
  SessionListItem,
  SessionDetailResponse,
  RouteAnalysisResponse,
  DynamicAxis,
} from '../types/api'
import type { SelectedCard } from '../types/analysis'
import { apiClient } from '../api/client'
import type { FilterState } from '../components/WordFilterPanel'
import type { GradientScheme } from '../utils/colorBlending'
import { LAYER_RANGES } from '../constants/layerRanges'

import { useAxisControls } from '../hooks/useAxisControls'
import { useClusteringConfig } from '../hooks/useClusteringConfig'
import { useSchemaManagement } from '../hooks/useSchemaManagement'
import Toolbar from '../components/toolbar/Toolbar'
import ExpertRoutesSection from '../components/analysis/ExpertRoutesSection'
import ClusterRoutesSection from '../components/analysis/ClusterRoutesSection'
import TemporalAnalysisSection from '../components/analysis/TemporalAnalysisSection'
import WindowAnalysis from '../components/analysis/WindowAnalysis'
import ContextSensitiveCard from '../components/analysis/ContextSensitiveCard'
import FilteredWordDisplay from '../components/FilteredWordDisplay'
import MUDTerminal from '../components/terminal/MUDTerminal'

export default function MUDApp() {
  // Session state
  const [selectedSession, setSelectedSession] = useState<string>('')
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [sessionDetails, setSessionDetails] = useState<SessionDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [serverBusy, setServerBusy] = useState(false)
  const [filterState, setFilterState] = useState<FilterState>({ labels: new Set() })

  // Visual encoding (axes, colors, gradients)
  const axes = useAxisControls()
  const {
    allAxes, colorAxisId, colorAxis2Id, shapeAxisId, gradient, selectedRange,
    outputAxes, outputColorAxisId, outputColorAxis2Id, outputGradient,
    colorAxis2, shapeAxis, secondaryGradient,
    primaryValues, secondaryValues,
    outputColorAxis, outputColorAxis2, outputSecondaryGradient,
    outputPrimaryValues, outputSecondaryValues, outputGroupingAxes,
    setAllAxes, setColorAxisId, setColorAxis2Id, setShapeAxisId,
    setGradient, setSelectedRange,
    setOutputAxes, setOutputColorAxisId, setOutputColorAxis2Id, setOutputGradient,
  } = axes

  // Expert tab controls
  const [topRoutes, setTopRoutes] = useState(10)
  const [showAllRoutes, setShowAllRoutes] = useState(false)

  // Clustering parameters
  const clustering = useClusteringConfig()

  // Route data
  const [currentRouteData, setCurrentRouteData] = useState<Record<string, RouteAnalysisResponse | null> | null>(null)
  const [currentClusterRouteData, setCurrentClusterRouteData] = useState<Record<string, RouteAnalysisResponse | null> | null>(null)
  const [elementDescriptions, setElementDescriptions] = useState<Record<string, string>>({})

  // Card panel state
  const [selectedCard, setSelectedCard] = useState<SelectedCard | null>(null)

  // Schema management
  const handleElementDescriptionsLoaded = useCallback((descs: Record<string, string>) => {
    setElementDescriptions(prev => ({ ...prev, ...descs }))
  }, [])
  const selectedSessions = useMemo(() => selectedSession ? [selectedSession] : [], [selectedSession])
  const schema = useSchemaManagement(selectedSessions, handleElementDescriptionsLoaded)
  const { availableSchemas, selectedSchema, setSelectedSchema } = schema

  // Sync clustering config when schema selected (same as ExperimentPage lines 186-202)
  useEffect(() => {
    if (!selectedSchema) return
    const schema = availableSchemas.find(s => s.name === selectedSchema)
    if (!schema?.params) return
    const p = schema.params
    if (p.reduction_dimensions) clustering.setReductionDims(p.reduction_dimensions)
    if (p.reduction_method) clustering.setReductionMethod(p.reduction_method)
    if (p.clustering_method) clustering.setClusteringMethod(p.clustering_method)
    if (p.embedding_source) clustering.setEmbeddingSource(p.embedding_source)
    if (p.layer_cluster_counts) {
      const counts = Object.values(p.layer_cluster_counts) as number[]
      if (counts.length > 0) {
        clustering.setGlobalClusterCount(counts[0])
        clustering.setUseAllLayersSameClusters(true)
      }
    }
  }, [selectedSchema, availableSchemas])

  // Load session list on mount
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const sessionList = await apiClient.listSessions()
        setSessions(sessionList)
      } catch (err) {
        setError('Failed to load sessions')
      } finally {
        setLoading(false)
      }
    }
    loadSessions()
  }, [])

  // Reset everything when session changes
  const resetForNewSession = useCallback(async (sessionId: string) => {
    setSelectedSession(sessionId)

    // Reset axes to defaults
    setAllAxes([])
    setColorAxisId('label')
    setColorAxis2Id('none')
    setShapeAxisId('none')
    setGradient('red-blue')
    setSelectedRange('range1')
    setOutputAxes([])
    setOutputColorAxisId('')
    setOutputColorAxis2Id('none')
    setOutputGradient('purple-green' as GradientScheme)

    // Clear data
    setCurrentRouteData(null)
    setCurrentClusterRouteData(null)
    setElementDescriptions({})
    setSelectedCard(null)
    setFilterState({ labels: new Set() })
    setSelectedSchema('')

    // Fetch session details
    if (sessionId) {
      try {
        const details = await apiClient.getSessionDetails(sessionId)
        setSessionDetails(details)
      } catch (err) {
        setError(`Failed to load session: ${sessionId}`)
      }
    } else {
      setSessionDetails(null)
    }
  }, [setAllAxes, setColorAxisId, setColorAxis2Id, setShapeAxisId, setGradient,
      setSelectedRange, setOutputAxes, setOutputColorAxisId, setOutputColorAxis2Id,
      setOutputGradient, setSelectedSchema])

  // Auto-detect axes from route analysis
  const handleRouteDataLoaded = useCallback((routeDataMap: Record<string, RouteAnalysisResponse | null>) => {
    setCurrentRouteData(routeDataMap)
    // Collect all input axes from responses
    const axesMap = new Map<string, DynamicAxis>()
    for (const data of Object.values(routeDataMap)) {
      if (data?.available_axes) {
        for (const axis of data.available_axes) {
          if (!axesMap.has(axis.id)) {
            axesMap.set(axis.id, axis)
          }
        }
      }
    }
    const detectedAxes = Array.from(axesMap.values())
    if (detectedAxes.length > 0) {
      setAllAxes(detectedAxes)
      if (!detectedAxes.find(a => a.id === colorAxisId)) {
        setColorAxisId(detectedAxes[0].id)
      }
    }

    // Collect output axes from responses
    const outputAxesMap = new Map<string, DynamicAxis>()
    for (const data of Object.values(routeDataMap)) {
      if (data?.output_available_axes) {
        for (const axis of data.output_available_axes) {
          if (!outputAxesMap.has(axis.id)) {
            outputAxesMap.set(axis.id, axis)
          }
        }
      }
    }
    const detectedOutputAxes = Array.from(outputAxesMap.values())
    setOutputAxes(detectedOutputAxes)
    if (outputColorAxisId !== '' && detectedOutputAxes.length > 0 && !detectedOutputAxes.find(a => a.id === outputColorAxisId)) {
      setOutputColorAxisId('')
    }
  }, [colorAxisId, outputColorAxisId])

  const handleClusterRouteDataLoaded = useCallback((routeDataMap: Record<string, RouteAnalysisResponse | null>) => {
    setCurrentClusterRouteData(routeDataMap)

    // Extract output axes from cluster route data
    const outputAxesMap = new Map<string, DynamicAxis>()
    for (const data of Object.values(routeDataMap)) {
      if (data?.output_available_axes) {
        for (const axis of data.output_available_axes) {
          if (!outputAxesMap.has(axis.id)) {
            outputAxesMap.set(axis.id, axis)
          }
        }
      }
    }
    const detectedOutputAxes = Array.from(outputAxesMap.values())
    if (detectedOutputAxes.length > 0) {
      setOutputAxes(prev => {
        const merged = new Map(prev.map(a => [a.id, a]))
        detectedOutputAxes.forEach(a => { if (!merged.has(a.id)) merged.set(a.id, a) })
        return Array.from(merged.values())
      })
    }
  }, [outputColorAxisId])

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Toolbar */}
      <Toolbar
        sessions={sessions}
        selectedSession={selectedSession}
        onSessionChange={resetForNewSession}
        sessionDetails={sessionDetails}
        axes={axes}
        topRoutes={topRoutes}
        showAllRoutes={showAllRoutes}
        onTopRoutesChange={setTopRoutes}
        onShowAllRoutesChange={setShowAllRoutes}
        clustering={clustering}
        schema={schema}
        selectedRange={selectedRange}
        filterState={filterState}
        onFilterStateChange={setFilterState}
        currentRouteData={currentRouteData}
      />

      {/* Quadrant Grid */}
      <div className="flex-1 grid grid-cols-2 grid-rows-2 gap-px bg-gray-300 overflow-hidden">
        {/* Q1: Viz */}
        <div className="bg-white overflow-y-auto overflow-x-auto p-2 space-y-4">
          {selectedSession && sessionDetails && (
            <>
              <ExpertRoutesSection
                sessionIds={selectedSessions}
                sessionData={sessionDetails}
                filterState={filterState}
                primaryValues={primaryValues}
                gradient={gradient}
                secondaryValues={secondaryValues}
                secondaryGradient={secondaryGradient}
                secondaryAxisId={colorAxis2Id !== 'none' ? colorAxis2Id : undefined}
                outputPrimaryValues={outputPrimaryValues}
                outputGradient={outputGradient}
                outputSecondaryValues={outputSecondaryValues}
                outputSecondaryGradient={outputSecondaryGradient}
                outputSecondaryAxisId={outputColorAxis2Id !== 'none' ? outputColorAxis2Id : undefined}
                outputColorAxisId={outputColorAxisId || undefined}
                outputGroupingAxes={outputGroupingAxes}
                clusteringSchema={selectedSchema || undefined}
                topRoutes={topRoutes}
                selectedRange={selectedRange}
                onRangeChange={setSelectedRange}
                showAllRoutes={showAllRoutes}
                onRouteDataLoaded={handleRouteDataLoaded}
                onCardSelect={setSelectedCard}
              />

              <ClusterRoutesSection
                sessionIds={selectedSessions}
                sessionData={sessionDetails}
                filterState={filterState}
                primaryValues={primaryValues}
                gradient={gradient}
                secondaryValues={secondaryValues}
                secondaryGradient={secondaryGradient}
                secondaryAxisId={colorAxis2Id !== 'none' ? colorAxis2Id : undefined}
                outputPrimaryValues={outputPrimaryValues}
                outputGradient={outputGradient}
                outputSecondaryValues={outputSecondaryValues}
                outputSecondaryGradient={outputSecondaryGradient}
                outputSecondaryAxisId={outputColorAxis2Id !== 'none' ? outputColorAxis2Id : undefined}
                outputColorAxisId={outputColorAxisId || undefined}
                outputGroupingAxes={outputGroupingAxes}
                shapeAxisId={shapeAxisId !== 'none' ? shapeAxisId : undefined}
                shapeAxis={shapeAxis}
                selectedRange={selectedRange}
                onRangeChange={setSelectedRange}
                layerClusterCounts={clustering.layerClusterCounts}
                clusteringMethod={clustering.clusteringMethod}
                reductionDimensions={clustering.reductionDims}
                embeddingSource={clustering.embeddingSource}
                reductionMethod={clustering.reductionMethod}
                useAllLayersSameClusters={clustering.useAllLayersSameClusters}
                setUseAllLayersSameClusters={clustering.setUseAllLayersSameClusters}
                globalClusterCount={clustering.globalClusterCount}
                setGlobalClusterCount={clustering.setGlobalClusterCount}
                clusteringDimSubset={clustering.clusteringDimSubset}
                clusteringSchema={selectedSchema || undefined}
                onRouteDataLoaded={handleClusterRouteDataLoaded}
                onCardSelect={setSelectedCard}
              />

              <TemporalAnalysisSection
                sessionId={selectedSession}
                clusterRouteData={currentClusterRouteData}
                clusteringSchema={selectedSchema}
                selectedRange={selectedRange}
              />
            </>
          )}
        </div>

        {/* Q2: Analysis */}
        <div className="bg-white overflow-y-auto overflow-x-hidden p-2">
          {selectedSession && (
            <>
              {/* Window-level statistical analysis */}
              {(() => {
                const routeMap = currentClusterRouteData || currentRouteData
                if (!routeMap) return null
                const currentRange = LAYER_RANGES[selectedRange as keyof typeof LAYER_RANGES]
                if (!currentRange) return null
                const lastWindow = currentRange.windows[currentRange.windows.length - 1]
                const lastData = routeMap[lastWindow?.id]
                if (!lastData) return null
                const reportKey = lastWindow ? `w_${lastWindow.layers[0]}_${lastWindow.layers[lastWindow.layers.length - 1]}` : undefined
                return (
                  <WindowAnalysis
                    routeData={lastData}
                    windowLabel={currentRange.label}
                    report={reportKey ? schema.schemaReports[reportKey] : undefined}
                    selectedSchema={selectedSchema || undefined}
                    primaryValues={primaryValues}
                    gradient={gradient}
                  />
                )
              })()}

              {/* Click card */}
              {selectedCard ? (() => {
                const d = selectedCard.data
                const descKey = selectedCard.type === 'expert'
                  ? `expert-${d.expertId || d.expert_id}-L${d.layer}`
                  : selectedCard.type === 'cluster'
                    ? `cluster-${d.clusterId || d.cluster_id}-L${d.layer}`
                    : `route-${d.signature}`

                let clusterAssignments: Record<string, number> | undefined
                if (selectedCard.type === 'route' && d.probe_id && currentClusterRouteData) {
                  for (const data of Object.values(currentClusterRouteData)) {
                    if (data?.probe_assignments?.[d.probe_id]) {
                      clusterAssignments = data.probe_assignments[d.probe_id]
                      break
                    }
                  }
                }

                return (
                  <ContextSensitiveCard
                    cardType={selectedCard.type}
                    selectedData={selectedCard.data}
                    primaryValues={primaryValues}
                    gradient={gradient}
                    elementDescription={elementDescriptions[descKey]}
                    clusterAssignments={clusterAssignments}
                    onClose={() => setSelectedCard(null)}
                  />
                )
              })() : (
                <div className="flex items-center justify-center py-8">
                  <p className="text-[10px] text-gray-400">Click a node or route for details</p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Q3: Terminal */}
        <div className="bg-gray-900 overflow-hidden">
          <MUDTerminal />
        </div>

        {/* Q4: Sentences */}
        <div className="bg-white overflow-auto p-2">
          {selectedSession && sessionDetails && (
            <FilteredWordDisplay
              sessionData={sessionDetails}
              filterState={filterState}
              primaryValues={primaryValues}
              gradient={gradient}
            />
          )}
        </div>
      </div>
    </div>
  )
}
