import { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import type {
  SessionListItem,
  SessionDetailResponse,
  RouteAnalysisResponse,
} from '../types/api'
import type { SelectedCard } from '../types/analysis'
import { apiClient } from '../api/client'
import { FlaskIcon } from '../components/icons/Icons'
import WordFilterPanel, { type FilterState } from '../components/WordFilterPanel'
import FilteredWordDisplay from '../components/FilteredWordDisplay'
import { getAxisPreview, type GradientScheme, GRADIENT_SCHEMES, GRADIENT_AUTO_PAIRS } from '../utils/colorBlending'
import type { DynamicAxis } from '../types/api'
import { LAYER_RANGES } from '../constants/layerRanges'

import TemporalAnalysisSection from '../components/analysis/TemporalAnalysisSection'
import ContextSensitiveCard from '../components/analysis/ContextSensitiveCard'
import WindowAnalysis from '../components/analysis/WindowAnalysis'
import ExpertRoutesSection from '../components/analysis/ExpertRoutesSection'
import ClusterRoutesSection from '../components/analysis/ClusterRoutesSection'

import { useAxisControls } from '../hooks/useAxisControls'
import { useClusteringConfig } from '../hooks/useClusteringConfig'
import { useSchemaManagement } from '../hooks/useSchemaManagement'

interface AxisControlsProps {
  allAxes: DynamicAxis[]
  colorAxisId: string
  colorAxis2Id: string
  shapeAxisId: string
  onColorAxisChange: (id: string) => void
  onColorAxis2Change: (id: string) => void
  onShapeAxisChange: (id: string) => void
  gradient: GradientScheme
  onGradientChange: (gradient: GradientScheme) => void
}

function AxisControls({
  allAxes,
  colorAxisId,
  colorAxis2Id,
  shapeAxisId,
  onColorAxisChange,
  onColorAxis2Change,
  onShapeAxisChange,
  gradient,
  onGradientChange
}: AxisControlsProps) {
  const colorAxis = allAxes.find(a => a.id === colorAxisId)
  const colorAxis2 = allAxes.find(a => a.id === colorAxis2Id)
  const autoSecondaryGradient = GRADIENT_AUTO_PAIRS[gradient]

  const primaryValues = colorAxis?.values || (colorAxis ? [colorAxis.label_a, colorAxis.label_b] : [])
  const secondaryValues = colorAxis2?.values || (colorAxis2 ? [colorAxis2.label_a, colorAxis2.label_b] : undefined)

  const preview = primaryValues.length > 0
    ? getAxisPreview(primaryValues, gradient, secondaryValues)
    : []

  return (
    <div className="space-y-1.5">
      {/* Color 1 + gradient picker */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-xs text-gray-500 font-medium">Color:</span>
        <select
          value={colorAxisId}
          onChange={(e) => onColorAxisChange(e.target.value)}
          className="px-1.5 py-0.5 text-xs border border-gray-300 rounded flex-1 min-w-0"
        >
          {allAxes.map(axis => (
            <option key={axis.id} value={axis.id}>{axis.label}</option>
          ))}
        </select>
        <select
          value={gradient}
          onChange={(e) => onGradientChange(e.target.value as GradientScheme)}
          className="px-1.5 py-0.5 text-xs border border-gray-300 rounded"
        >
          {Object.entries(GRADIENT_SCHEMES).map(([key, scheme]) => (
            <option key={key} value={key}>{scheme.name}</option>
          ))}
        </select>
      </div>

      {/* Color 2 (secondary blend axis) */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-xs text-gray-500 font-medium">Blend:</span>
        <select
          value={colorAxis2Id}
          onChange={(e) => onColorAxis2Change(e.target.value)}
          className="px-1.5 py-0.5 text-xs border border-gray-300 rounded flex-1 min-w-0"
        >
          <option value="none">None</option>
          {allAxes.filter(a => a.id !== colorAxisId).map(axis => (
            <option key={axis.id} value={axis.id}>{axis.label}</option>
          ))}
        </select>
        {colorAxis2Id !== 'none' && (
          <span className="text-xs text-gray-400">{GRADIENT_SCHEMES[autoSecondaryGradient]?.name}</span>
        )}
      </div>

      {/* Shape axis (trajectory only) */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-xs text-gray-500 font-medium">Shape:</span>
        <select
          value={shapeAxisId}
          onChange={(e) => onShapeAxisChange(e.target.value)}
          className="px-1.5 py-0.5 text-xs border border-gray-300 rounded flex-1 min-w-0"
        >
          <option value="none">None</option>
          {allAxes.map(axis => (
            <option key={axis.id} value={axis.id}>{axis.label}</option>
          ))}
        </select>
      </div>

      {/* Color preview */}
      {preview.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          {preview.map(({ label, color }) => (
            <div key={label} className="flex items-center gap-1" title={label}>
              <div
                className="rounded-sm border border-gray-300 flex-shrink-0"
                style={{ backgroundColor: color, width: '12px', height: '12px' }}
              />
              <span className="text-xs text-gray-600">{label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ExperimentPage() {
  const { id } = useParams<{ id: string }>()
  const [selectedSessions, setSelectedSessions] = useState<string[]>([])
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [mergedSessionDetails, setMergedSessionDetails] = useState<SessionDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [serverBusy, setServerBusy] = useState(false)
  const [filterState, setFilterState] = useState<FilterState>({
    labels: new Set()
  })

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

  // LLM Insights state
  const [currentRouteData, setCurrentRouteData] = useState<Record<string, RouteAnalysisResponse | null> | null>(null)
  const [currentClusterRouteData, setCurrentClusterRouteData] = useState<Record<string, RouteAnalysisResponse | null> | null>(null)
  const [elementDescriptions, setElementDescriptions] = useState<Record<string, string>>({})

  // Card panel state (right column)
  const [selectedCard, setSelectedCard] = useState<SelectedCard | null>(null)

  // Clustering schema management (loads schemas and reports per session)
  const handleElementDescriptionsLoaded = useCallback((descs: Record<string, string>) => {
    setElementDescriptions(prev => ({ ...prev, ...descs }))
  }, [])
  const { availableSchemas, selectedSchema, schemaReports, setSelectedSchema } =
    useSchemaManagement(selectedSessions, handleElementDescriptionsLoaded)

  // Sync clustering config state when a saved schema is selected
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

  // Derive available labels from route analysis available_axes (for filter panel)
  const availableLabels = useMemo(() => {
    if (!currentRouteData) return []
    const labels = new Set<string>()
    for (const data of Object.values(currentRouteData)) {
      if (data?.available_axes) {
        for (const axis of data.available_axes) {
          if (axis.id === 'label') {
            if (axis.values) {
              axis.values.forEach(v => labels.add(v))
            } else {
              labels.add(axis.label_a)
              labels.add(axis.label_b)
            }
          }
        }
      }
    }
    return Array.from(labels)
  }, [currentRouteData])

  // Derive available steps for the step filter dropdown
  const availableSteps = useMemo(() => {
    const steps = new Set<number>()
    mergedSessionDetails?.sentences?.forEach(s => {
      if ((s as any).step != null) steps.add((s as any).step)
    })
    return Array.from(steps).sort((a, b) => a - b)
  }, [mergedSessionDetails])

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
      // Auto-select colorAxisId if not already set to a valid axis
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
    // Keep current selection if it's '' (match input) or a valid axis
    if (outputColorAxisId !== '' && detectedOutputAxes.length > 0 && !detectedOutputAxes.find(a => a.id === outputColorAxisId)) {
      setOutputColorAxisId('')
    }
  }, [colorAxisId, outputColorAxisId])

  const handleClusterRouteDataLoaded = useCallback((routeDataMap: Record<string, RouteAnalysisResponse | null>) => {
    setCurrentClusterRouteData(routeDataMap)

    // Also extract output axes from cluster route data
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

  useEffect(() => {
    loadSessions()
  }, [])

  useEffect(() => {
    if (selectedSessions.length > 0) {
      loadAndMergeSessions()
    } else {
      setMergedSessionDetails(null)
    }
  }, [selectedSessions])

  const loadAndMergeSessions = async () => {
    try {
      const details = await Promise.all(
        selectedSessions.map(id => apiClient.getSessionDetails(id))
      )

      if (details.length === 1) {
        setMergedSessionDetails(details[0])
        return
      }

      // Merge labels by union across sessions
      const mergedLabels = new Set<string>()
      for (const d of details) {
        (d.labels || []).forEach((l: string) => mergedLabels.add(l))
      }

      // Merge sentences across sessions
      const mergedSentences = details.flatMap(d => d.sentences || [])

      setMergedSessionDetails({
        manifest: details[0].manifest,
        data_lake_paths: details[0].data_lake_paths,
        labels: Array.from(mergedLabels),
        target_word: details[0].target_word,
        sentences: mergedSentences.length > 0 ? mergedSentences : undefined
      })
    } catch (err) {
      console.error('Failed to load session details:', err)
      setMergedSessionDetails(null)
    }
  }

  const loadSessions = async () => {
    try {
      setLoading(true)
      setError(null)
      const sessionsData = await apiClient.listSessions()
      setSessions(sessionsData)
      setServerBusy(false)

      // Filter to only completed sessions for analysis
      const completedSessions = sessionsData.filter(s => s.state === 'completed')

      // Only auto-select if session ID is in URL and exists
      if (id && completedSessions.find((s: SessionListItem) => s.session_id === id)) {
        setSelectedSessions([id])
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load sessions'
      // If we already have sessions loaded, show a non-blocking warning instead of replacing the page
      if (sessions.length > 0 && msg.includes('timed out')) {
        setServerBusy(true)
      } else {
        setError(msg)
      }
      console.error('Failed to load sessions:', err)
    } finally {
      setLoading(false)
    }
  }

  const selectedSessionData = selectedSessions.length > 0 ? sessions.find(s => s.session_id === selectedSessions[0]) : undefined

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading experiment data...</p>
        </div>
      </div>
    )
  }

  if (error || sessions.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <FlaskIcon className="w-6 h-6 text-gray-400 mx-auto mb-2" />
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">
            {error ? 'Error Loading Data' : 'No Probe Sessions'}
          </h2>
          <p className="text-gray-600 mb-6">
            {error || 'Create a probe session first to analyze experiments.'}
          </p>
          {error ? (
            <button
              onClick={loadSessions}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors shadow-sm"
            >
              Retry
            </button>
          ) : (
            <a
              href="/"
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors shadow-sm"
            >
              Go to Workspace
            </a>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Server busy banner */}
      {serverBusy && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center justify-between text-sm">
          <span className="text-amber-800">Server is busy running a temporal capture. Some data may be stale.</span>
          <button onClick={() => { setServerBusy(false); loadSessions() }} className="text-amber-600 hover:text-amber-800 font-medium">Retry</button>
        </div>
      )}

      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="px-8 py-6">
          <h1 className="text-2xl font-bold text-gray-900">Concept MRI Experiment</h1>
          <p className="text-sm text-gray-600">Analyze MoE routing patterns and latent trajectories</p>
        </div>
      </div>

      <div className="flex h-[calc(100vh-88px)]">
        {/* Left Sidebar - Sessions + Word Filters */}
        <div className="bg-white shadow-sm border-r flex flex-col overflow-y-auto sidebar-narrow">
          {/* Session Selector */}
          <div className="p-2 border-b">
            <h3 className="text-xs font-semibold text-gray-700 mb-1">Sessions</h3>
            <div className="max-h-32 overflow-y-auto space-y-1">
              {sessions.filter(s => s.state === 'completed').map((session) => (
                <label key={session.session_id} className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedSessions.includes(session.session_id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedSessions(prev => [...prev, session.session_id])
                      } else {
                        setSelectedSessions(prev => prev.filter(id => id !== session.session_id))
                      }
                    }}
                    className="w-3 h-3 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="ml-1.5 text-xs text-gray-700 truncate">{session.session_name}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Word Filter Panel (absorbed from middle column) */}
          {mergedSessionDetails && (
            <div className="p-2 border-b space-y-3 flex-1 overflow-y-auto">
              <WordFilterPanel
                sessionData={mergedSessionDetails}
                selectedFilters={filterState}
                onFiltersChange={setFilterState}
                isLoading={!mergedSessionDetails}
              />
              <FilteredWordDisplay
                sessionData={mergedSessionDetails}
                filterState={filterState}
                isLoading={!mergedSessionDetails}
                primaryValues={primaryValues}
                gradient={gradient}
              />
            </div>
          )}

          {/* Session Stats */}
          {selectedSessionData && (
            <div className="p-2 border-t mt-auto">
              <div className="flex justify-between items-center">
                <span className="text-[10px] text-gray-500">Probes</span>
                <span className="text-xs font-medium text-gray-900">{selectedSessionData.probe_count}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[10px] text-gray-500">Status</span>
                <span className="text-xs font-medium text-gray-900">{selectedSessionData.state}</span>
              </div>
            </div>
          )}
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col">
          {selectedSessions.length > 0 ? (
            <>
              {/* Top Bar — Analysis + Appearance Controls */}
              <div className="flex gap-4 p-2 border-b bg-white shadow-sm flex-shrink-0">
                {/* Left: Analysis Controls */}
                <div className="flex-1 space-y-1.5">
                  <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Analysis</h4>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px]">
                    {/* Source */}
                    <div className="flex items-center gap-1">
                      <span className="text-gray-400">Source</span>
                      <select value={clustering.embeddingSource} onChange={e => clustering.setEmbeddingSource(e.target.value)}
                        className="px-1 py-0.5 border border-gray-300 rounded text-[10px]">
                        <option value="expert_output">expert output</option>
                        <option value="residual_stream">residual stream</option>
                      </select>
                    </div>
                    {/* Reduction */}
                    <div className="flex items-center gap-1">
                      <span className="text-gray-400">Reduce</span>
                      <select value={clustering.reductionMethod} onChange={e => clustering.setReductionMethod(e.target.value)}
                        className="px-1 py-0.5 border border-gray-300 rounded text-[10px]">
                        <option value="pca">PCA</option>
                        <option value="umap">UMAP</option>
                      </select>
                      <input type="number" value={clustering.reductionDims} onChange={e => clustering.setReductionDims(Number(e.target.value))}
                        min={2} max={256} className="w-8 px-1 py-0.5 border border-gray-300 rounded text-[10px]" />
                      <span className="text-gray-400">D</span>
                    </div>
                    {/* Clustering */}
                    <div className="flex items-center gap-1">
                      <span className="text-gray-400">Cluster</span>
                      <select value={clustering.clusteringMethod} onChange={e => clustering.setClusteringMethod(e.target.value)}
                        className="px-1 py-0.5 border border-gray-300 rounded text-[10px]">
                        <option value="hierarchical">hierarchical</option>
                        <option value="kmeans">kmeans</option>
                      </select>
                    </div>
                    {/* K */}
                    <div className="flex items-center gap-1">
                      <span className="text-gray-400">K</span>
                      <input type="number" value={clustering.globalClusterCount} onChange={e => clustering.setGlobalClusterCount(Number(e.target.value))}
                        min={2} max={16} className="w-8 px-1 py-0.5 border border-gray-300 rounded text-[10px]" />
                    </div>
                    {/* Schema */}
                    {availableSchemas.length > 0 && (
                      <div className="flex items-center gap-1">
                        <span className="text-gray-400">Schema</span>
                        <select value={selectedSchema} onChange={(e) => setSelectedSchema(e.target.value)}
                          className="px-1 py-0.5 border border-gray-300 rounded text-[10px] max-w-[120px]">
                          <option value="">fresh</option>
                          {availableSchemas.map(s => (
                            <option key={s.name} value={s.name}>{s.name}</option>
                          ))}
                        </select>
                      </div>
                    )}
                    {/* Expert Routes */}
                    <div className="flex items-center gap-1">
                      <label className="flex items-center gap-1 text-[10px] text-gray-600">
                        <input type="checkbox" checked={showAllRoutes} onChange={(e) => setShowAllRoutes(e.target.checked)}
                          className="w-3 h-3 rounded border-gray-300 text-blue-600" />
                        All routes
                      </label>
                      {!showAllRoutes && (
                        <>
                          <span className="text-gray-400">Top</span>
                          <input type="number" value={topRoutes} onChange={(e) => setTopRoutes(parseInt(e.target.value))}
                            min={5} max={100} className="w-10 px-1 py-0.5 border border-gray-300 rounded text-[10px]" />
                        </>
                      )}
                    </div>
                  </div>
                  {/* Schema summary (when schema selected) */}
                  {selectedSchema && (
                    <div className="text-[9px] text-gray-400 font-mono">
                      {(() => {
                        const schema = availableSchemas.find(s => s.name === selectedSchema)
                        if (!schema?.params) return selectedSchema
                        const p = schema.params
                        const source = p.embedding_source === 'residual_stream' ? 'residual' : 'expert'
                        const method = (p.reduction_method || 'pca').toUpperCase()
                        const dims = p.reduction_dimensions || '?'
                        const clustering_m = p.clustering_method || '?'
                        const counts = p.layer_cluster_counts || {}
                        const kValues = [...new Set(Object.values(counts) as number[])]
                        const kStr = kValues.length === 1 ? `K=${kValues[0]}` : kValues.map((v, i) => `K=${v}`).join('/')
                        return `${source} · ${method} ${dims}D · ${clustering_m} · ${kStr}`
                      })()}
                    </div>
                  )}
                  {/* Labeling instruction */}
                  {selectedSchema && selectedSessions[0] && (() => {
                    const currentRange = LAYER_RANGES[selectedRange as keyof typeof LAYER_RANGES]
                    if (!currentRange) return null
                    const lastWindow = currentRange.windows[currentRange.windows.length - 1]
                    const windowStr = lastWindow ? `${lastWindow.layers[0]}-${lastWindow.layers[lastWindow.layers.length - 1]}` : '22-23'
                    const instruction = `/analyze ${selectedSessions[0]} schema ${selectedSchema} window ${windowStr}`
                    return (
                      <div
                        className="text-[9px] font-mono bg-blue-50 border border-blue-200 rounded px-1.5 py-0.5 cursor-pointer hover:bg-blue-100 inline-block"
                        title="Click to copy"
                        onClick={e => {
                          const el = e.currentTarget
                          const range = document.createRange()
                          range.selectNodeContents(el)
                          const sel = window.getSelection()
                          sel?.removeAllRanges()
                          sel?.addRange(range)
                          navigator.clipboard?.writeText(el.textContent || '')
                        }}
                      >
                        {instruction}
                      </div>
                    )
                  })()}
                </div>

                {/* Right: Appearance Controls */}
                <div className="flex-1 space-y-1.5">
                  <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Appearance</h4>
                  <AxisControls
                    allAxes={allAxes}
                    colorAxisId={colorAxisId}
                    colorAxis2Id={colorAxis2Id}
                    shapeAxisId={shapeAxisId}
                    onColorAxisChange={setColorAxisId}
                    onColorAxis2Change={setColorAxis2Id}
                    onShapeAxisChange={setShapeAxisId}
                    gradient={gradient}
                    onGradientChange={setGradient}
                  />
                  {/* Output Color Controls */}
                  {outputAxes.length > 0 && (
                    <div className="border-t border-gray-200 pt-1.5">
                      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1">Output Colors</h4>
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px]">
                        <div className="flex items-center gap-1">
                          <span className="text-gray-400">Color:</span>
                          <select value={outputColorAxisId} onChange={(e) => setOutputColorAxisId(e.target.value)}
                            className="px-1 py-0.5 border border-gray-300 rounded text-[10px]">
                            <option value="">Match input</option>
                            {outputAxes.map(axis => (
                              <option key={axis.id} value={axis.id}>{axis.label}</option>
                            ))}
                          </select>
                          <select value={outputGradient} onChange={(e) => setOutputGradient(e.target.value as GradientScheme)}
                            className="px-1 py-0.5 border border-gray-300 rounded text-[10px]">
                            {Object.entries(GRADIENT_SCHEMES).map(([key, scheme]) => (
                              <option key={key} value={key}>{scheme.name}</option>
                            ))}
                          </select>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-gray-400">Blend:</span>
                          <select value={outputColorAxis2Id} onChange={(e) => setOutputColorAxis2Id(e.target.value)}
                            className="px-1 py-0.5 border border-gray-300 rounded text-[10px]">
                            <option value="none">None</option>
                            {outputAxes.filter(a => a.id !== outputColorAxisId).map(axis => (
                              <option key={axis.id} value={axis.id}>{axis.label}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                      {/* Output color preview */}
                      {(() => {
                        const outPrimaryValues = outputColorAxis?.values || (outputColorAxis ? [outputColorAxis.label_a, outputColorAxis.label_b] : [])
                        const outSecondaryValues = outputColorAxis2?.values || (outputColorAxis2 ? [outputColorAxis2.label_a, outputColorAxis2.label_b] : undefined)
                        const outPreview = outPrimaryValues.length > 0
                          ? getAxisPreview(outPrimaryValues, outputGradient, outputColorAxis2Id !== 'none' ? outSecondaryValues : undefined)
                          : []
                        return outPreview.length > 0 ? (
                          <div className="flex items-center gap-1.5 flex-wrap mt-1">
                            {outPreview.map(({ label, color }) => (
                              <div key={label} className="flex items-center gap-0.5" title={label}>
                                <div className="rounded-sm border border-gray-300 flex-shrink-0" style={{ backgroundColor: color, width: '10px', height: '10px' }} />
                                <span className="text-[9px] text-gray-600">{label}</span>
                              </div>
                            ))}
                          </div>
                        ) : null
                      })()}
                    </div>
                  )}
                </div>
              </div>

              {/* Visualization Area */}
              <div className="flex-1 flex overflow-x-auto">
                {/* Scrollable main content */}
                <div className="flex-1 min-w-0 overflow-y-auto p-2 space-y-4">
                  <ExpertRoutesSection
                    sessionIds={selectedSessions}
                    sessionData={mergedSessionDetails}
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
                    sessionData={mergedSessionDetails}
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
                    steps={clustering.steps}
                    setSteps={clustering.setSteps}
                    availableSteps={availableSteps}
                    clusteringSchema={selectedSchema || undefined}
                    onRouteDataLoaded={handleClusterRouteDataLoaded}
                    onCardSelect={setSelectedCard}
                  />

                  <TemporalAnalysisSection
                    sessionId={selectedSessions[0]}
                    clusterRouteData={currentClusterRouteData}
                    clusteringSchema={selectedSchema}
                    selectedRange={selectedRange}
                  />
                </div>

                {/* Right column — window analysis + click card */}
                <div className="w-96 max-w-[384px] flex-shrink-0 border-l bg-white overflow-y-auto overflow-x-hidden p-2">
                  {/* Window-level statistical analysis (always visible) */}
                  {(() => {
                    const routeMap = currentClusterRouteData || currentRouteData
                    if (!routeMap) return null
                    const currentRange = LAYER_RANGES[selectedRange as keyof typeof LAYER_RANGES]
                    if (!currentRange) return null
                    const lastWindow = currentRange.windows[currentRange.windows.length - 1]
                    const lastData = routeMap[lastWindow?.id]
                    if (!lastData) return null
                    const reportKey = lastWindow ? `w_${lastWindow.layers[0]}_${lastWindow.layers[lastWindow.layers.length - 1]}` : undefined
                    return <WindowAnalysis routeData={lastData} windowLabel={currentRange.label} report={reportKey ? schemaReports[reportKey] : undefined} selectedSchema={selectedSchema || undefined} primaryValues={primaryValues} gradient={gradient} />
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
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <FlaskIcon className="w-6 h-6 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-500 text-lg">Please select a probe session to begin analysis</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
