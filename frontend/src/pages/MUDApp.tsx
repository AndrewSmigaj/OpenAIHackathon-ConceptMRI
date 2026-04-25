import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import type {
  SessionListItem,
  SessionDetailResponse,
  RouteAnalysisResponse,
  DynamicAxis,
} from '../types/api'
import type { SelectedCard } from '../types/analysis'
import { apiClient } from '../api/client'
import type { GradientScheme, AmbiguityBlend } from '../utils/colorBlending'
import { LAYER_RANGES } from '../constants/layerRanges'
import type { RoomContext, RoomEnteredPayload, VizPreset } from '../types/evennia'

import { useAxisControls } from '../hooks/useAxisControls'
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
  const [, setLoading] = useState(true)
  const [, setError] = useState<string | null>(null)

  // Visual encoding (axes, colors, gradients)
  const axes = useAxisControls()
  const {
    colorAxis2Id, shapeAxisId, gradient, selectedRange,
    outputColorAxisId, outputColorAxis2Id, outputGradient,
    shapeAxis, secondaryGradient,
    primaryValues, secondaryValues,
    outputSecondaryGradient,
    outputPrimaryValues, outputSecondaryValues, outputGroupingAxes,
    setAllAxes, setColorAxisId, setColorAxis2Id, setShapeAxisId,
    setGradient, setSelectedRange,
    setOutputAxes, setOutputColorAxisId, setOutputColorAxis2Id, setOutputGradient,
  } = axes

  // Expert tab controls
  const [topRoutes, setTopRoutes] = useState(10)
  const [showAllRoutes, setShowAllRoutes] = useState(false)

  // Trajectory display
  const [maxTrajectories, setMaxTrajectories] = useState<number>(200)

  // Ambiguity blend
  const [ambiguityBlendEnabled, setAmbiguityBlendEnabled] = useState(false)
  const [ambiguousValue, setAmbiguousValue] = useState<string>('')

  // Route data
  const [currentRouteData, setCurrentRouteData] = useState<Record<string, RouteAnalysisResponse | null> | null>(null)
  const [currentClusterRouteData, setCurrentClusterRouteData] = useState<Record<string, RouteAnalysisResponse | null> | null>(null)
  const [elementDescriptions, setElementDescriptions] = useState<Record<string, string>>({})

  // Card panel state
  const [selectedCard, setSelectedCard] = useState<SelectedCard | null>(null)

  // Analysis triggers — lifted from sections so Toolbar's unified Run can fire all three
  const [runExpert, setRunExpert] = useState<(() => void) | null>(null)
  const [runClusterSankey, setRunClusterSankey] = useState<(() => void) | null>(null)
  const [runTrajectory, setRunTrajectory] = useState<(() => void) | null>(null)

  const handleRunAll = useCallback(() => {
    runExpert?.(); runClusterSankey?.(); runTrajectory?.()
  }, [runExpert, runClusterSankey, runTrajectory])

  const canRunAll = !!(selectedSession && runExpert && runClusterSankey && runTrajectory)

  const handleExpertAnalysisReady = useCallback((fn: () => void) => setRunExpert(() => fn), [])
  const handleSankeyAnalysisReady = useCallback((fn: () => void) => setRunClusterSankey(() => fn), [])
  const handleTrajectoryAnalysisReady = useCallback((fn: () => void) => setRunTrajectory(() => fn), [])

  // MUD room context
  const [roomContext, setRoomContext] = useState<RoomContext | null>(null)

  // Schema management
  const handleElementDescriptionsLoaded = useCallback((descs: Record<string, string>) => {
    setElementDescriptions(prev => ({ ...prev, ...descs }))
  }, [])
  const selectedSessions = useMemo(() => selectedSession ? [selectedSession] : [], [selectedSession])
  const schema = useSchemaManagement(selectedSessions, handleElementDescriptionsLoaded)
  const { availableSchemas, selectedSchema, setSelectedSchema } = schema

  // When schema changes, default maxTrajectories to its sample_size
  useEffect(() => {
    const meta = availableSchemas.find(s => s.name === selectedSchema)
    if (meta?.sample_size) {
      setMaxTrajectories(meta.sample_size)
    }
  }, [selectedSchema, availableSchemas])

  // When secondary axis changes, default the ambiguous pole to first value
  useEffect(() => {
    if (secondaryValues && secondaryValues.length === 2) {
      if (!ambiguousValue || !secondaryValues.includes(ambiguousValue)) {
        setAmbiguousValue(secondaryValues[0])
      }
    } else if (ambiguityBlendEnabled) {
      setAmbiguityBlendEnabled(false)
    }
  }, [secondaryValues, ambiguousValue, ambiguityBlendEnabled])

  const ambiguityBlend = useMemo<AmbiguityBlend | undefined>(() => {
    if (!ambiguityBlendEnabled || !ambiguousValue) return undefined
    return { enabled: true, ambiguousValue, mixRatio: 0.6 }
  }, [ambiguityBlendEnabled, ambiguousValue])

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

    setCurrentRouteData(null)
    setCurrentClusterRouteData(null)
    setElementDescriptions({})
    setSelectedCard(null)
    setSelectedSchema('')
    setAmbiguityBlendEnabled(false)
    setAmbiguousValue('')

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
      if (!detectedAxes.find(a => a.id === axes.colorAxisId)) {
        setColorAxisId(detectedAxes[0].id)
      }
    }

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
  }, [axes.colorAxisId, outputColorAxisId, setAllAxes, setColorAxisId, setOutputAxes, setOutputColorAxisId])

  const handleClusterRouteDataLoaded = useCallback((routeDataMap: Record<string, RouteAnalysisResponse | null>) => {
    setCurrentClusterRouteData(routeDataMap)

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
  }, [setOutputAxes])

  // Apply viz preset from room OOB event
  const applyPreset = useCallback((preset: VizPreset) => {
    if (preset.primary_axis) setColorAxisId(preset.primary_axis)
    if (preset.gradient) setGradient(preset.gradient as GradientScheme)
    if (preset.layer_range) setSelectedRange(preset.layer_range)
    if (preset.clustering_schema) setSelectedSchema(preset.clustering_schema)
    if (preset.top_routes) setTopRoutes(preset.top_routes)
  }, [setColorAxisId, setGradient, setSelectedRange, setSelectedSchema])

  // Generation counter to handle rapid room navigation
  const navigationGenRef = useRef(0)

  // Handle OOB events from Evennia
  const handleOOB = useCallback((cmdname: string, args: unknown[], kwargs: Record<string, unknown>) => {
    if (cmdname === 'room_entered') {
      const payload = (args[0] || kwargs || {}) as RoomEnteredPayload
      const gen = ++navigationGenRef.current

      setRoomContext({
        role: (payload.role === 'researcher' ? 'researcher' : 'visitor') as RoomContext['role'],
        roomType: (payload.room_type || 'hub') as RoomContext['roomType'],
      })

      if (payload.session_id) {
        resetForNewSession(payload.session_id).then(() => {
          if (gen === navigationGenRef.current && payload.viz_preset) {
            applyPreset(payload.viz_preset)
          }
        })
      }
    } else if (cmdname === 'room_left') {
      setRoomContext(null)
    }
  }, [resetForNewSession, applyPreset])

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
        schema={schema}
        selectedRange={selectedRange}
        maxTrajectories={maxTrajectories}
        onMaxTrajectoriesChange={setMaxTrajectories}
        ambiguityBlendEnabled={ambiguityBlendEnabled}
        onAmbiguityBlendToggle={setAmbiguityBlendEnabled}
        ambiguousValue={ambiguousValue}
        onAmbiguousValueChange={setAmbiguousValue}
        roomContext={roomContext}
        onRunAll={handleRunAll}
        canRunAll={canRunAll}
      />

      {/* Quadrant Grid */}
      <div className="flex-1 grid grid-cols-2 gap-0.5 bg-gray-400 overflow-hidden" style={{ gridTemplateRows: '2fr 1fr' }}>
        {/* Q1: Viz */}
        <div className="bg-white overflow-y-auto overflow-x-auto p-2 space-y-4">
          {selectedSession && sessionDetails && selectedSchema && (
            <>
              <ExpertRoutesSection
                sessionIds={selectedSessions}
                sessionData={sessionDetails}
                schemaName={selectedSchema}
                primaryValues={primaryValues}
                gradient={gradient}
                secondaryValues={secondaryValues}
                secondaryGradient={secondaryGradient}
                secondaryAxisId={colorAxis2Id !== 'none' ? colorAxis2Id : undefined}
                ambiguityBlend={ambiguityBlend}
                outputPrimaryValues={outputPrimaryValues}
                outputGradient={outputGradient}
                outputSecondaryValues={outputSecondaryValues}
                outputSecondaryGradient={outputSecondaryGradient}
                outputSecondaryAxisId={outputColorAxis2Id !== 'none' ? outputColorAxis2Id : undefined}
                outputColorAxisId={outputColorAxisId || undefined}
                outputGroupingAxes={outputGroupingAxes}
                topRoutes={topRoutes}
                selectedRange={selectedRange}
                onRangeChange={setSelectedRange}
                showAllRoutes={showAllRoutes}
                onRouteDataLoaded={handleRouteDataLoaded}
                onCardSelect={setSelectedCard}
                onExpertAnalysisReady={handleExpertAnalysisReady}
              />

              <ClusterRoutesSection
                sessionIds={selectedSessions}
                sessionData={sessionDetails}
                schemaName={selectedSchema}
                primaryValues={primaryValues}
                gradient={gradient}
                secondaryValues={secondaryValues}
                secondaryGradient={secondaryGradient}
                secondaryAxisId={colorAxis2Id !== 'none' ? colorAxis2Id : undefined}
                ambiguityBlend={ambiguityBlend}
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
                maxTrajectories={maxTrajectories}
                onRouteDataLoaded={handleClusterRouteDataLoaded}
                onCardSelect={setSelectedCard}
                onSankeyAnalysisReady={handleSankeyAnalysisReady}
                onTrajectoryAnalysisReady={handleTrajectoryAnalysisReady}
                selectedProbeId={selectedCard?.type === 'route' ? (selectedCard.data as any)?.probe_id ?? null : null}
              />

              <TemporalAnalysisSection
                sessionId={selectedSession}
                clusterRouteData={currentClusterRouteData}
                clusteringSchema={selectedSchema}
                selectedRange={selectedRange}
              />
            </>
          )}
          {selectedSession && sessionDetails && !selectedSchema && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
              Select a clustering schema in the toolbar to view routes and trajectories.
              Build new schemas via Claude Code: <code className="font-mono bg-amber-100 px-1 rounded">/cluster</code> OP-1.
            </div>
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
          <MUDTerminal onOOB={handleOOB} />
        </div>

        {/* Q4: Sentences */}
        <div className="bg-white overflow-auto p-2 border border-gray-200">
          {selectedSession && sessionDetails && (
            <FilteredWordDisplay
              sessionData={sessionDetails}
              filterState={{ labels: new Set() }}
              primaryValues={primaryValues}
              gradient={gradient}
            />
          )}
        </div>
      </div>
    </div>
  )
}
