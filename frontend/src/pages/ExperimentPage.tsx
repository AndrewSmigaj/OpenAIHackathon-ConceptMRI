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

import LLMAnalysisPanel from '../components/analysis/LLMAnalysisPanel'
import ContextSensitiveCard from '../components/analysis/ContextSensitiveCard'
import ExpertRoutesSection from '../components/analysis/ExpertRoutesSection'
import ClusterRoutesSection from '../components/analysis/ClusterRoutesSection'

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
  const [filterState, setFilterState] = useState<FilterState>({
    labels: new Set()
  })

  // Multi-axis visual encoding state
  const [allAxes, setAllAxes] = useState<DynamicAxis[]>([])
  const [colorAxisId, setColorAxisId] = useState<string>('label')
  const [colorAxis2Id, setColorAxis2Id] = useState<string>('none')
  const [shapeAxisId, setShapeAxisId] = useState<string>('none')
  const [gradient, setGradient] = useState<GradientScheme>('red-blue')
  const [selectedRange, setSelectedRange] = useState<string>('range1')

  // Derive colorLabelA/B from selected axis (for downstream components)
  const colorAxis = allAxes.find(a => a.id === colorAxisId)
  const colorAxis2 = allAxes.find(a => a.id === colorAxis2Id)
  const shapeAxis = allAxes.find(a => a.id === shapeAxisId)
  const colorLabelA = colorAxis?.label_a || ''
  const colorLabelB = colorAxis?.label_b || ''
  const secondaryCategoryA = colorAxis2?.label_a
  const secondaryCategoryB = colorAxis2?.label_b
  const secondaryGradient = GRADIENT_AUTO_PAIRS[gradient]
  const primaryAxisValues = colorAxis?.values || (colorAxis ? [colorAxis.label_a, colorAxis.label_b] : undefined)
  const secondaryAxisValues = colorAxis2?.values || (colorAxis2 ? [colorAxis2.label_a, colorAxis2.label_b] : undefined)

  // Expert tab controls
  const [topRoutes, setTopRoutes] = useState(10)
  const [showAllRoutes, setShowAllRoutes] = useState(false)

  // Latent tab controls
  const [layerClusterCounts, setLayerClusterCounts] = useState<{[key: number]: number}>({})
  const [clusteringMethod, setClusteringMethod] = useState('kmeans')
  const [reductionDims, setReductionDims] = useState(3)
  const [embeddingSource, setEmbeddingSource] = useState<string>('expert_output')
  const [reductionMethod, setReductionMethod] = useState<string>('pca')
  // Cluster configuration mode
  const [useAllLayersSameClusters, setUseAllLayersSameClusters] = useState(true)  // Default to "same for all"
  const [globalClusterCount, setGlobalClusterCount] = useState(4)  // Default to 4 clusters
  const [clusteringDimSubset, setClusteringDimSubset] = useState<number[] | null>(null)  // null = all dims
  const [clusterDimInput, setClusterDimInput] = useState('all')  // UI text input

  // LLM Insights state
  const [currentRouteData, setCurrentRouteData] = useState<Record<string, RouteAnalysisResponse | null> | null>(null)
  const [currentClusterRouteData, setCurrentClusterRouteData] = useState<Record<string, RouteAnalysisResponse | null> | null>(null)
  const [elementDescriptions, setElementDescriptions] = useState<Record<string, string>>({})

  // Card panel state (right column)
  const [selectedCard, setSelectedCard] = useState<SelectedCard | null>(null)

  // Derive available labels from route analysis available_axes (for filter panel)
  const availableLabels = useMemo(() => {
    if (!currentRouteData) return []
    const labels = new Set<string>()
    for (const data of Object.values(currentRouteData)) {
      if (data?.available_axes) {
        for (const axis of data.available_axes) {
          if (axis.id === 'label') {
            labels.add(axis.label_a)
            labels.add(axis.label_b)
          }
        }
      }
    }
    return Array.from(labels)
  }, [currentRouteData])

  // Auto-detect axes from route analysis
  const handleRouteDataLoaded = useCallback((routeDataMap: Record<string, RouteAnalysisResponse | null>) => {
    setCurrentRouteData(routeDataMap)
    // Collect all axes from responses
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
  }, [colorAxisId])

  const handleClusterRouteDataLoaded = useCallback((routeDataMap: Record<string, RouteAnalysisResponse | null>) => {
    setCurrentClusterRouteData(routeDataMap)
  }, [])

  const handleElementDescriptionsLoaded = useCallback((descs: Record<string, string>) => {
    setElementDescriptions(prev => ({ ...prev, ...descs }))
  }, [])

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

      // Filter to only completed sessions for analysis
      const completedSessions = sessionsData.filter(s => s.state === 'completed')

      // Only auto-select if session ID is in URL and exists
      if (id && completedSessions.find((s: SessionListItem) => s.session_id === id)) {
        setSelectedSessions([id])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions')
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
          <FlaskIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
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
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="px-8 py-6">
          <h1 className="text-2xl font-bold text-gray-900">Concept MRI Experiment</h1>
          <p className="text-sm text-gray-600">Analyze MoE routing patterns and latent trajectories</p>
        </div>
      </div>

      <div className="flex h-[calc(100vh-88px)]">
        {/* Left Sidebar - Session, Tabs, Controls */}
        <div className="bg-white shadow-sm border-r flex flex-col overflow-y-auto sidebar-narrow">
          {/* Session Selector — checkbox list for multi-session */}
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

          {/* Controls Section */}
          {selectedSessions.length > 0 && (
            <div className="p-3 border-b">
              <h3 className="text-xs font-semibold text-gray-900 mb-2">Controls</h3>

              <div className="space-y-4">
                {/* Shared Controls */}
                <div>
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
                </div>

                {/* Expert Controls */}
                <div className="border-t border-gray-200 pt-2">
                  <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Expert Routes</h4>
                  <div className="space-y-2">
                    <label className="flex items-center gap-1.5 text-[11px] text-gray-700">
                      <input
                        type="checkbox"
                        checked={showAllRoutes}
                        onChange={(e) => setShowAllRoutes(e.target.checked)}
                        className="w-3 h-3 rounded border-gray-300 text-blue-600"
                      />
                      Show all routes
                    </label>
                    {!showAllRoutes && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-gray-500">Top</span>
                        <input
                          type="number"
                          value={topRoutes}
                          onChange={(e) => setTopRoutes(parseInt(e.target.value))}
                          min="5"
                          max="100"
                          className="w-14 px-1.5 py-0.5 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                        <span className="text-[10px] text-gray-500">routes</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Cluster Controls */}
                <div className="border-t border-gray-200 pt-2">
                  <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Cluster Routes</h4>
                  <div className="space-y-2">
                    {/* Row 1: Source + Method */}
                    <div className="grid grid-cols-2 gap-1.5">
                      <div>
                        <label className="block text-[10px] text-gray-500 mb-0.5">Source</label>
                        <select
                          value={embeddingSource}
                          onChange={(e) => setEmbeddingSource(e.target.value)}
                          className="w-full px-1.5 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="expert_output">Expert Output</option>
                          <option value="residual_stream">Residual Stream</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[10px] text-gray-500 mb-0.5">Method</label>
                        <select
                          value={reductionMethod}
                          onChange={(e) => setReductionMethod(e.target.value)}
                          className="w-full px-1.5 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="pca">PCA</option>
                          <option value="umap">UMAP</option>
                        </select>
                      </div>
                    </div>

                    {/* Row 2: Dims + Clustering Method */}
                    <div className="grid grid-cols-2 gap-1.5">
                      <div>
                        <label className="block text-[10px] text-gray-500 mb-0.5">Dims</label>
                        <select
                          value={reductionDims}
                          onChange={(e) => setReductionDims(parseInt(e.target.value))}
                          className="w-full px-1.5 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          {[2, 3, 5, 10, 15, 20, 50, 128].map(d => (
                            <option key={d} value={d}>{d}D</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-[10px] text-gray-500 mb-0.5">Clustering</label>
                        <select
                          value={clusteringMethod}
                          onChange={(e) => setClusteringMethod(e.target.value)}
                          className="w-full px-1.5 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="kmeans">K-Means</option>
                          <option value="hierarchical">Hierarchical</option>
                          <option value="dbscan">DBSCAN</option>
                        </select>
                      </div>
                    </div>

                    {/* Row 3: K + Per-layer toggle */}
                    <div className="grid grid-cols-2 gap-1.5 items-end">
                      <div>
                        <label className="block text-[10px] text-gray-500 mb-0.5">K (clusters)</label>
                        <input
                          type="number"
                          value={globalClusterCount}
                          onChange={(e) => setGlobalClusterCount(parseInt(e.target.value) || 2)}
                          min="2"
                          max="20"
                          className="w-full px-1.5 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </div>
                      <label className="flex items-center gap-1 text-[10px] text-gray-600 pb-1">
                        <input
                          type="checkbox"
                          checked={!useAllLayersSameClusters}
                          onChange={(e) => setUseAllLayersSameClusters(!e.target.checked)}
                          className="w-3 h-3 rounded border-gray-300 text-blue-600"
                        />
                        Per-layer K
                      </label>
                    </div>

                    {/* Per-layer cluster counts (hidden by default) */}
                    {!useAllLayersSameClusters && (() => {
                      const currentRange = selectedRange as keyof typeof LAYER_RANGES
                      const rangeDef = LAYER_RANGES[currentRange]
                      if (!rangeDef) return null
                      const allLayers = new Set<number>()
                      rangeDef.windows.forEach(w => w.layers.forEach(l => allLayers.add(l)))
                      return (
                        <div className="grid grid-cols-3 gap-1">
                          {Array.from(allLayers).sort((a, b) => a - b).map(layer => (
                            <div key={layer}>
                              <label className="block text-[9px] text-gray-400">L{layer}</label>
                              <input
                                type="number"
                                value={layerClusterCounts[layer] || 4}
                                onChange={(e) => {
                                  const newCounts = { ...layerClusterCounts }
                                  newCounts[layer] = parseInt(e.target.value)
                                  setLayerClusterCounts(newCounts)
                                }}
                                min="2"
                                max="20"
                                className="w-full px-1 py-0.5 text-[10px] border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                              />
                            </div>
                          ))}
                        </div>
                      )
                    })()}

                    {/* Clustering dim subset (only shown when dims > 3) */}
                    {reductionDims > 3 && (
                      <div>
                        <label className="block text-[10px] text-gray-500 mb-0.5">Cluster dims</label>
                        <input
                          type="text"
                          value={clusterDimInput}
                          onChange={(e) => {
                            const val = e.target.value.trim()
                            setClusterDimInput(val)
                            if (val === '' || val.toLowerCase() === 'all') {
                              setClusteringDimSubset(null)
                            } else {
                              const dims = val.split(',')
                                .map(s => parseInt(s.trim()) - 1)
                                .filter(n => !isNaN(n) && n >= 0 && n < reductionDims)
                              setClusteringDimSubset(dims.length > 0 ? dims : null)
                            }
                          }}
                          placeholder="all"
                          className="w-full px-1.5 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                          title="Enter 'all' or comma-separated dim numbers (1-indexed), e.g. 1,2,5"
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Session Stats */}
          {selectedSessionData && (
            <div className="p-4">
              <h3 className="text-xs font-semibold text-gray-700 mb-2">Session Info</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-600">Probes</span>
                  <span className="font-medium text-sm text-gray-900">{selectedSessionData.probe_count}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-600">Status</span>
                  <span className="font-medium text-sm text-gray-900">{selectedSessionData.state}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Main Content Area - 3 Column Layout */}
        <div className="flex-1 flex">
          {selectedSessions.length > 0 ? (
            <>
              {/* Middle Column - Word Lists */}
              <div className="bg-gray-50 border-r p-4 space-y-4 word-panel-narrow">
                {mergedSessionDetails && (
                  <>
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
                      colorLabelA={colorLabelA}
                      colorLabelB={colorLabelB}
                      gradient={gradient}
                    />
                  </>
                )}
              </div>

              {/* Right Column - Visualization + LLM + Card Panel */}
              <div className="flex-1 flex overflow-x-auto">
                {/* Scrollable main content */}
                <div className="flex-1 min-w-[640px] overflow-y-auto p-4 space-y-4">
                  <ExpertRoutesSection
                    sessionIds={selectedSessions}
                    sessionData={mergedSessionDetails}
                    filterState={filterState}
                    colorLabelA={colorLabelA}
                    colorLabelB={colorLabelB}
                    gradient={gradient}
                    secondaryCategoryA={secondaryCategoryA}
                    secondaryCategoryB={secondaryCategoryB}
                    secondaryGradient={secondaryGradient}
                    secondaryAxisId={colorAxis2Id !== 'none' ? colorAxis2Id : undefined}
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
                    colorLabelA={colorLabelA}
                    colorLabelB={colorLabelB}
                    gradient={gradient}
                    secondaryCategoryA={secondaryCategoryA}
                    secondaryCategoryB={secondaryCategoryB}
                    secondaryGradient={secondaryGradient}
                    secondaryAxisId={colorAxis2Id !== 'none' ? colorAxis2Id : undefined}
                    shapeAxisId={shapeAxisId !== 'none' ? shapeAxisId : undefined}
                    shapeAxis={shapeAxis}
                    primaryAxisValues={primaryAxisValues}
                    secondaryAxisValues={secondaryAxisValues}
                    selectedRange={selectedRange}
                    onRangeChange={setSelectedRange}
                    layerClusterCounts={layerClusterCounts}
                    clusteringMethod={clusteringMethod}
                    reductionDimensions={reductionDims}
                    embeddingSource={embeddingSource}
                    reductionMethod={reductionMethod}
                    useAllLayersSameClusters={useAllLayersSameClusters}
                    setUseAllLayersSameClusters={setUseAllLayersSameClusters}
                    globalClusterCount={globalClusterCount}
                    setGlobalClusterCount={setGlobalClusterCount}
                    clusteringDimSubset={clusteringDimSubset}
                    onRouteDataLoaded={handleClusterRouteDataLoaded}
                    onCardSelect={setSelectedCard}
                  />

                  <LLMAnalysisPanel
                    sessionId={selectedSessions[0]}
                    expertRouteData={currentRouteData}
                    clusterRouteData={currentClusterRouteData}
                    selectedRange={selectedRange}
                    onElementDescriptionsLoaded={handleElementDescriptionsLoaded}
                  />
                </div>

                {/* Right card panel — shows when something is clicked */}
                {selectedCard && (() => {
                  const d = selectedCard.data
                  const descKey = selectedCard.type === 'expert'
                    ? `expert-${d.expertId || d.expert_id}-L${d.layer}`
                    : selectedCard.type === 'cluster'
                      ? `cluster-${d.clusterId || d.cluster_id}-L${d.layer}`
                      : `route-${d.signature}`

                  // Look up cluster assignments for trajectory clicks
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
                    <div className="w-72 flex-shrink-0 border-l bg-white overflow-y-auto p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-semibold text-gray-900">Details</h3>
                        <button
                          onClick={() => setSelectedCard(null)}
                          className="text-gray-400 hover:text-gray-600 text-lg leading-none"
                        >
                          &times;
                        </button>
                      </div>
                      <ContextSensitiveCard
                        cardType={selectedCard.type}
                        selectedData={selectedCard.data}
                        colorLabelA={colorLabelA}
                        colorLabelB={colorLabelB}
                        gradient={gradient}
                        elementDescription={elementDescriptions[descKey]}
                        clusterAssignments={clusterAssignments}
                      />
                    </div>
                  )
                })()}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <FlaskIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 text-lg">Please select a probe session to begin analysis</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
