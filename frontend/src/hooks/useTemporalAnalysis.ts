import { useState, useEffect, useMemo, useCallback } from 'react'
import type { RouteAnalysisResponse } from '../types/api'
import type { BasinOption, TemporalRunMetadata, TemporalLagData, TemporalLagPoint, RunGroup, AggregateLine } from '../types/temporal'
import { apiClient } from '../api/client'

interface UseTemporalAnalysisProps {
  sessionId: string | null
  clusterRouteData: Record<string, RouteAnalysisResponse | null> | null
  clusteringSchema: string | null
}

export interface TemporalAnalysisState {
  // Basin selection
  availableLayers: number[]
  basinLayer: number | null
  setBasinLayer: React.Dispatch<React.SetStateAction<number | null>>
  layerBasinOptions: BasinOption[]
  basinA: number | null
  setBasinA: React.Dispatch<React.SetStateAction<number | null>>
  basinB: number | null
  setBasinB: React.Dispatch<React.SetStateAction<number | null>>
  instructionText: string

  // Runs
  runs: TemporalRunMetadata[]
  loadRuns: () => Promise<void>
  loadingRuns: boolean
  selectedRunIds: string[]
  toggleRunSelection: (runId: string) => void
  lagDataMap: Record<string, TemporalLagData>

  // Grouping & aggregation
  runGroups: RunGroup[]
  aggregateLines: Record<string, AggregateLine>
  highlightedRunId: string | null
  setHighlightedRunId: React.Dispatch<React.SetStateAction<string | null>>
  showAggregate: boolean
  setShowAggregate: React.Dispatch<React.SetStateAction<boolean>>
  toggleGroupSelection: (group: RunGroup) => void

  // Scrubber
  scrubberPosition: number
  setScrubberPosition: React.Dispatch<React.SetStateAction<number>>
  scrubberPoint: TemporalLagPoint | null
  maxPosition: number

  // Metrics
  lagMetrics: {
    perRun: Record<string, { lag: number; processingMode: string }>
    perGroup: Record<string, { meanLag: number; stdLag: number; count: number; mode: string }>
    deltaPersistence: number | null
  }
}

/** Build a condition key from a run's metadata */
function conditionKey(run: TemporalRunMetadata): string {
  return `${run.clustering_schema || 'default'}_${run.basin_a_cluster_id}_${run.basin_b_cluster_id}_${run.basin_layer}_${run.processing_mode}_${run.sequence_config}`
}

/** Build a human-readable label for a condition */
function conditionLabel(run: TemporalRunMetadata, basinOptions?: BasinOption[]): string {
  let fromLabel: string, toLabel: string
  if (run.sequence_config === 'block_ba') {
    fromLabel = basinName(run.basin_b_cluster_id, run.basin_layer, basinOptions) || 'B'
    toLabel = basinName(run.basin_a_cluster_id, run.basin_layer, basinOptions) || 'A'
  } else {
    fromLabel = basinName(run.basin_a_cluster_id, run.basin_layer, basinOptions) || 'A'
    toLabel = basinName(run.basin_b_cluster_id, run.basin_layer, basinOptions) || 'B'
  }
  const mode = run.processing_mode.replace('expanding_', '').replace('_', ' ')
  return `${fromLabel}→${toLabel} ${mode}`
}

/** Get a short name for a basin cluster — uses dominant category if available */
function basinName(clusterId: number, layer: number, basinOptions?: BasinOption[]): string | null {
  if (!basinOptions) return null
  const opt = basinOptions.find(o => o.clusterId === clusterId && o.layer === layer)
  return opt?.dominantCategory || null
}

/** Color palette for condition groups */
const CONDITION_COLORS: Record<string, string> = {
  'cache_on_block_ab': '#3b82f6',    // blue
  'cache_off_block_ab': '#f59e0b',   // amber
  'cache_on_block_ba': '#10b981',    // emerald
  'cache_off_block_ba': '#f43f5e',   // rose
}

function conditionColor(run: TemporalRunMetadata): string {
  const modeKey = run.processing_mode.replace('expanding_', '') + '_' + run.sequence_config
  return CONDITION_COLORS[modeKey] || '#6b7280'
}

export function useTemporalAnalysis({ sessionId, clusterRouteData, clusteringSchema }: UseTemporalAnalysisProps): TemporalAnalysisState {
  // Basin selection state
  const [basinLayer, setBasinLayer] = useState<number | null>(null)
  const [basinA, setBasinA] = useState<number | null>(null)
  const [basinB, setBasinB] = useState<number | null>(null)

  // Temporal runs state
  const [runs, setRuns] = useState<TemporalRunMetadata[]>([])
  const [lagDataMap, setLagDataMap] = useState<Record<string, TemporalLagData>>({})
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([])
  const [loadingRuns, setLoadingRuns] = useState(false)

  // Highlight and aggregate state
  const [highlightedRunId, setHighlightedRunId] = useState<string | null>(null)
  const [showAggregate, setShowAggregate] = useState(true)

  // Scrubber state
  const [scrubberPosition, setScrubberPosition] = useState(0)

  // Derive basin options from cluster route data
  const { basinOptions, availableLayers } = useMemo(() => {
    if (!clusterRouteData) return { basinOptions: [] as BasinOption[], availableLayers: [] as number[] }

    const options: BasinOption[] = []
    const layers = new Set<number>()

    for (const windowData of Object.values(clusterRouteData)) {
      if (!windowData?.nodes) continue
      for (const node of windowData.nodes) {
        // Parse cluster ID and layer from node name (e.g. "L22C3")
        const match = node.name?.match(/^L(\d+)C(\d+)$/)
        if (!match) continue

        const layer = parseInt(match[1])
        const clusterId = parseInt(match[2])
        layers.add(layer)

        // Compute purity from label_distribution
        const dist = node.label_distribution || {}
        const total = Object.values(dist).reduce((s, v) => s + v, 0)
        if (total === 0) continue

        const entries = Object.entries(dist).sort((a, b) => b[1] - a[1])
        const dominant = entries[0]
        const purity = Math.round((dominant[1] / total) * 100)

        // Avoid duplicates (same cluster can appear in multiple windows)
        if (options.some(o => o.clusterId === clusterId && o.layer === layer)) continue

        options.push({
          clusterId,
          layer,
          label: `L${layer}C${clusterId} — ${dominant[0]} (${purity}%)`,
          dominantCategory: dominant[0],
          purity,
          tokenCount: node.token_count || total,
        })
      }
    }

    return {
      basinOptions: options.sort((a, b) => a.layer - b.layer || a.clusterId - b.clusterId),
      availableLayers: Array.from(layers).sort((a, b) => a - b),
    }
  }, [clusterRouteData])

  // Auto-select first layer when available
  useEffect(() => {
    if (availableLayers.length > 0 && basinLayer === null) {
      setBasinLayer(availableLayers[availableLayers.length - 1]) // default to deepest layer
    }
  }, [availableLayers, basinLayer])

  // Filter basin options by selected layer
  const layerBasinOptions = useMemo(
    () => basinOptions.filter(o => o.layer === basinLayer),
    [basinOptions, basinLayer]
  )

  // Generate instruction text for Claude Code
  const instructionText = useMemo(() => {
    if (!sessionId || basinA === null || basinB === null || basinLayer === null) return ''

    const basinAOpt = layerBasinOptions.find(o => o.clusterId === basinA)
    const basinBOpt = layerBasinOptions.find(o => o.clusterId === basinB)
    const aLabel = basinAOpt?.dominantCategory || `C${basinA}`
    const bLabel = basinBOpt?.dominantCategory || `C${basinB}`

    return `Run temporal capture on session ${sessionId}: basin_a=${basinA} (${aLabel}), basin_b=${basinB} (${bLabel}), layer=${basinLayer}, schema=${clusteringSchema || 'default'}, expanding_cache_on, 20/block`
  }, [sessionId, basinA, basinB, basinLayer, clusteringSchema, layerBasinOptions])

  // Load temporal runs for this session
  const loadRuns = useCallback(async () => {
    if (!sessionId) return
    setLoadingRuns(true)
    try {
      const data = await apiClient.getTemporalRuns(sessionId)
      setRuns(data)
      // Auto-select all runs
      setSelectedRunIds(data.map(r => r.temporal_run_id))
    } catch {
      setRuns([])
    } finally {
      setLoadingRuns(false)
    }
  }, [sessionId])

  useEffect(() => { loadRuns() }, [loadRuns])

  // Load lag data for selected runs
  useEffect(() => {
    if (!sessionId || !clusteringSchema || runs.length === 0) return

    const loadLagData = async () => {
      const newMap: Record<string, TemporalLagData> = {}
      for (const run of runs) {
        if (lagDataMap[run.temporal_run_id]) {
          newMap[run.temporal_run_id] = lagDataMap[run.temporal_run_id]
          continue
        }
        try {
          const data = await apiClient.getTemporalLagData({
            source_session_id: sessionId,
            temporal_session_id: run.new_session_id,
            clustering_schema: clusteringSchema,
            basin_a_cluster_id: run.basin_a_cluster_id,
            basin_b_cluster_id: run.basin_b_cluster_id,
            basin_layer: run.basin_layer,
          })
          newMap[run.temporal_run_id] = data
        } catch (err) {
          console.error(`Failed to load lag data for run ${run.temporal_run_id}:`, err)
        }
      }
      setLagDataMap(newMap)
    }
    loadLagData()
  }, [sessionId, clusteringSchema, runs]) // eslint-disable-line react-hooks/exhaustive-deps

  // Group runs by condition
  const runGroups: RunGroup[] = useMemo(() => {
    const groups = new Map<string, RunGroup>()
    for (const run of runs) {
      const key = conditionKey(run)
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          label: conditionLabel(run, basinOptions),
          color: conditionColor(run),
          runs: [],
        })
      }
      groups.get(key)!.runs.push(run)
    }
    return Array.from(groups.values())
  }, [runs, basinOptions])

  // Compute aggregate (mean) lines per group
  const aggregateLines: Record<string, AggregateLine> = useMemo(() => {
    const result: Record<string, AggregateLine> = {}

    for (const group of runGroups) {
      // Collect lag data for all runs in this group that are selected and have data
      const groupLagArrays: number[][] = []
      let maxPos = 0

      for (const run of group.runs) {
        if (!selectedRunIds.includes(run.temporal_run_id)) continue
        const lagData = lagDataMap[run.temporal_run_id]
        if (!lagData) continue

        const sorted = [...lagData.points].sort((a, b) => a.position - b.position)
        const projections = sorted.map(p => p.projection)
        groupLagArrays.push(projections)
        if (sorted.length > maxPos) maxPos = sorted.length
      }

      if (groupLagArrays.length < 2) continue // need ≥2 runs for meaningful aggregate

      const positions: number[] = []
      const meanProjection: number[] = []
      const stdProjection: number[] = []

      for (let i = 0; i < maxPos; i++) {
        const vals = groupLagArrays.map(arr => arr[i]).filter(v => v !== undefined)
        if (vals.length === 0) continue

        positions.push(i)
        const mean = vals.reduce((s, v) => s + v, 0) / vals.length
        meanProjection.push(mean)
        const variance = vals.reduce((s, v) => s + (v - mean) ** 2, 0) / vals.length
        stdProjection.push(Math.sqrt(variance))
      }

      result[group.key] = { positions, meanProjection, stdProjection }
    }

    return result
  }, [runGroups, selectedRunIds, lagDataMap])

  // Get current scrubber point info (from highlighted run, or first selected run)
  const scrubberPoint: TemporalLagPoint | null = useMemo(() => {
    const targetRunId = highlightedRunId || selectedRunIds[0]
    if (!targetRunId) return null
    const lagData = lagDataMap[targetRunId]
    if (!lagData) return null
    return lagData.points.find(p => p.position === scrubberPosition) || null
  }, [highlightedRunId, selectedRunIds, lagDataMap, scrubberPosition])

  // Max position across selected runs
  const maxPosition = useMemo(() => {
    let max = 0
    for (const runId of selectedRunIds) {
      const lagData = lagDataMap[runId]
      if (lagData) {
        const runMax = Math.max(...lagData.points.map(p => p.position))
        if (runMax > max) max = runMax
      }
    }
    return max
  }, [selectedRunIds, lagDataMap])

  // Compute lag metrics (now with per-group aggregation)
  const lagMetrics = useMemo(() => {
    const perRun: Record<string, { lag: number; processingMode: string }> = {}

    for (const runId of selectedRunIds) {
      const lagData = lagDataMap[runId]
      if (!lagData) continue

      const boundary = lagData.regime_boundary
      const postBoundary = lagData.points.filter(p => p.position >= boundary)

      // Routing lag: first position after boundary where projection > 0.5 for 3 consecutive
      let lag = postBoundary.length // default to no transition
      for (let i = 0; i < postBoundary.length - 2; i++) {
        if (postBoundary[i].projection > 0.5 &&
            postBoundary[i + 1].projection > 0.5 &&
            postBoundary[i + 2].projection > 0.5) {
          lag = postBoundary[i].position - boundary
          break
        }
      }

      perRun[runId] = { lag, processingMode: lagData.processing_mode }
    }

    // Compute per-group mean lag ± std
    const perGroup: Record<string, { meanLag: number; stdLag: number; count: number; mode: string }> = {}
    for (const group of runGroups) {
      const lags = group.runs
        .filter(r => perRun[r.temporal_run_id])
        .map(r => perRun[r.temporal_run_id].lag)
      if (lags.length === 0) continue
      const mean = lags.reduce((s, v) => s + v, 0) / lags.length
      const variance = lags.reduce((s, v) => s + (v - mean) ** 2, 0) / lags.length
      perGroup[group.key] = {
        meanLag: mean,
        stdLag: Math.sqrt(variance),
        count: lags.length,
        mode: group.runs[0].processing_mode,
      }
    }

    // Compute ΔPersistence from group means
    const cacheOnGroups = Object.values(perGroup).filter(g => g.mode === 'expanding_cache_on')
    const cacheOffGroups = Object.values(perGroup).filter(g => g.mode === 'expanding_cache_off')
    const deltaPersistence = cacheOnGroups.length > 0 && cacheOffGroups.length > 0
      ? cacheOnGroups[0].meanLag - cacheOffGroups[0].meanLag
      : null

    return { perRun, perGroup, deltaPersistence }
  }, [selectedRunIds, lagDataMap, runGroups])

  // Toggle run selection
  const toggleRunSelection = useCallback((runId: string) => {
    setSelectedRunIds(prev =>
      prev.includes(runId)
        ? prev.filter(id => id !== runId)
        : [...prev, runId]
    )
  }, [])

  // Toggle all runs in a group
  const toggleGroupSelection = useCallback((group: RunGroup) => {
    const groupIds = group.runs.map(r => r.temporal_run_id)
    const allSelected = groupIds.every(id => selectedRunIds.includes(id))
    if (allSelected) {
      setSelectedRunIds(prev => prev.filter(id => !groupIds.includes(id)))
    } else {
      setSelectedRunIds(prev => [...new Set([...prev, ...groupIds])])
    }
  }, [selectedRunIds])

  return {
    // Basin selection
    availableLayers,
    basinLayer, setBasinLayer,
    layerBasinOptions,
    basinA, setBasinA,
    basinB, setBasinB,
    instructionText,

    // Runs
    runs, loadRuns, loadingRuns,
    selectedRunIds, toggleRunSelection,
    lagDataMap,

    // Grouping & aggregation
    runGroups,
    aggregateLines,
    highlightedRunId, setHighlightedRunId,
    showAggregate, setShowAggregate,
    toggleGroupSelection,

    // Scrubber
    scrubberPosition, setScrubberPosition,
    scrubberPoint,
    maxPosition,

    // Metrics
    lagMetrics,
  }
}
