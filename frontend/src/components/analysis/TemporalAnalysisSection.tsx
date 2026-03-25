import React, { useState, useEffect, useRef, useCallback } from 'react'
import * as echarts from 'echarts'
import type { RouteAnalysisResponse } from '../../types/api'
import type { TemporalLagPoint } from '../../types/temporal'
import { useTemporalAnalysis } from '../../hooks/useTemporalAnalysis'

interface TemporalAnalysisSectionProps {
  sessionId: string
  clusterRouteData: Record<string, RouteAnalysisResponse | null> | null
  clusteringSchema: string | null
  selectedRange: string
  onScrubberProbeChange?: (probeId: string | null) => void
  onTemporalSessionIds?: (sessionIds: string[]) => void
}

export default function TemporalAnalysisSection({
  sessionId,
  clusterRouteData,
  clusteringSchema,
  selectedRange,
  onScrubberProbeChange,
  onTemporalSessionIds,
}: TemporalAnalysisSectionProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [copiedInstruction, setCopiedInstruction] = useState(false)
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)

  const {
    availableLayers,
    basinLayer, setBasinLayer,
    layerBasinOptions,
    basinA, setBasinA,
    basinB, setBasinB,
    instructionText,
    runs, loadRuns, loadingRuns,
    selectedRunIds, toggleRunSelection,
    lagDataMap,
    scrubberPosition, setScrubberPosition,
    scrubberPoint,
    maxPosition,
    lagMetrics,
  } = useTemporalAnalysis({ sessionId, clusterRouteData, clusteringSchema })

  // Emit temporal session IDs when selected runs change
  useEffect(() => {
    if (!onTemporalSessionIds) return
    const ids = runs
      .filter(r => selectedRunIds.includes(r.temporal_run_id))
      .map(r => r.new_session_id)
    onTemporalSessionIds(ids)
  }, [selectedRunIds, runs, onTemporalSessionIds])

  // Emit scrubber probe change
  useEffect(() => {
    onScrubberProbeChange?.(scrubberPoint?.probe_id || null)
  }, [scrubberPoint, onScrubberProbeChange])

  // Copy instruction text
  const handleCopy = useCallback(() => {
    if (!instructionText) return
    navigator.clipboard.writeText(instructionText)
    setCopiedInstruction(true)
    setTimeout(() => setCopiedInstruction(false), 2000)
  }, [instructionText])

  // --- ECharts lag chart ---
  useEffect(() => {
    if (!chartRef.current) return

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current)
    }
    const chart = chartInstance.current

    // Build series — one per selected run
    const series: any[] = []
    const modeColors: Record<string, string> = {
      'expanding_cache_on': '#3b82f6',
      'expanding_cache_off': '#f59e0b',
      'single_cache_on': '#10b981',
    }

    let regimeBoundary = 0

    for (const runId of selectedRunIds) {
      const lagData = lagDataMap[runId]
      if (!lagData) continue

      const run = runs.find(r => r.temporal_run_id === runId)
      regimeBoundary = lagData.regime_boundary

      const data = lagData.points
        .sort((a, b) => a.position - b.position)
        .map(p => [p.position, p.projection])

      series.push({
        name: run ? run.processing_mode.replace('expanding_', '').replace('_', ' ') : runId,
        type: 'line',
        data,
        smooth: false,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: {
          width: 2,
          color: modeColors[lagData.processing_mode] || '#6b7280',
        },
        itemStyle: {
          color: modeColors[lagData.processing_mode] || '#6b7280',
        },
        markLine: series.length === 0 ? {
          silent: true,
          symbol: 'none',
          data: [
            { xAxis: regimeBoundary, lineStyle: { type: 'dashed', color: '#ef4444', width: 1.5 }, label: { formatter: 'regime boundary', fontSize: 9, color: '#ef4444' } },
            { yAxis: 0, lineStyle: { type: 'dotted', color: '#6b7280', width: 1 }, label: { formatter: 'basin A (0)', fontSize: 8, color: '#6b7280', position: 'insideEndTop' } },
            { yAxis: 1, lineStyle: { type: 'dotted', color: '#6b7280', width: 1 }, label: { formatter: 'basin B (1)', fontSize: 8, color: '#6b7280', position: 'insideEndTop' } },
          ],
        } : undefined,
      })
    }

    // Scrubber indicator — dot on chart
    if (scrubberPoint && selectedRunIds.length > 0) {
      series.push({
        type: 'scatter',
        data: [[scrubberPoint.position, scrubberPoint.projection]],
        symbol: 'circle',
        symbolSize: 12,
        itemStyle: { color: '#111', borderColor: '#fff', borderWidth: 2 },
        z: 10,
      })
    }

    const option: echarts.EChartsOption = {
      animation: false,
      legend: {
        show: true,
        bottom: 0,
        textStyle: { fontSize: 9 },
        itemWidth: 16,
        itemHeight: 8,
      },
      grid: { left: 50, right: 20, top: 20, bottom: 50 },
      xAxis: {
        type: 'value',
        name: 'sentence position',
        nameTextStyle: { fontSize: 9, color: '#999' },
        axisLabel: { fontSize: 9 },
        min: 0,
        max: maxPosition > 0 ? maxPosition : undefined,
      },
      yAxis: {
        type: 'value',
        name: 'basin A \u2190 projection \u2192 basin B',
        nameTextStyle: { fontSize: 9, color: '#999' },
        axisLabel: { fontSize: 9 },
        min: -0.3,
        max: 1.3,
        splitLine: { lineStyle: { type: 'dashed', color: '#e5e7eb' } },
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (Array.isArray(params)) return ''
          const [pos, proj] = params.data
          return `pos ${pos}<br/>projection: ${proj?.toFixed(3)}`
        },
      },
      series,
    }

    chart.setOption(option, true)

    return () => {}
  }, [selectedRunIds, lagDataMap, runs, scrubberPoint, maxPosition])

  // Resize
  useEffect(() => {
    const chart = chartInstance.current
    if (!chart) return
    const observer = new ResizeObserver(() => chart.resize())
    if (chartRef.current) observer.observe(chartRef.current)
    return () => observer.disconnect()
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      chartInstance.current?.dispose()
      chartInstance.current = null
    }
  }, [])

  // Sentence text at scrubber position (from first selected run's metadata)
  const scrubberSentence = (() => {
    if (!scrubberPoint) return null
    return scrubberPoint.sentence_text || null
  })()

  const hasRuns = runs.length > 0
  const hasLagData = selectedRunIds.some(id => lagDataMap[id])

  return (
    <div className="border-t mt-4 pt-3">
      {/* Header */}
      <div
        className="flex items-center justify-between cursor-pointer select-none mb-2"
        onClick={() => setCollapsed(!collapsed)}
      >
        <h3 className="text-sm font-semibold text-gray-700">
          Temporal Analysis
        </h3>
        <span className="text-xs text-gray-400">{collapsed ? '\u25b8' : '\u25be'}</span>
      </div>

      {collapsed ? null : (
        <div className="space-y-3">
          {/* Basin Selection */}
          <div className="bg-gray-50 rounded p-2 space-y-1.5">
            <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">Basin Selection</p>

            {/* Layer selector */}
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500 w-12">Layer</label>
              <select
                className="text-xs border rounded px-1.5 py-0.5 flex-1"
                value={basinLayer ?? ''}
                onChange={e => setBasinLayer(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">--</option>
                {availableLayers.map(l => (
                  <option key={l} value={l}>Layer {l}</option>
                ))}
              </select>
            </div>

            {/* Basin A */}
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500 w-12">Basin A</label>
              <select
                className="text-xs border rounded px-1.5 py-0.5 flex-1"
                value={basinA ?? ''}
                onChange={e => setBasinA(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">--</option>
                {layerBasinOptions.map(o => (
                  <option key={o.clusterId} value={o.clusterId}>{o.label}</option>
                ))}
              </select>
            </div>

            {/* Basin B */}
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500 w-12">Basin B</label>
              <select
                className="text-xs border rounded px-1.5 py-0.5 flex-1"
                value={basinB ?? ''}
                onChange={e => setBasinB(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">--</option>
                {layerBasinOptions
                  .filter(o => o.clusterId !== basinA)
                  .map(o => (
                    <option key={o.clusterId} value={o.clusterId}>{o.label}</option>
                  ))}
              </select>
            </div>
          </div>

          {/* Instruction text */}
          {instructionText && (
            <div className="relative bg-slate-800 text-slate-200 rounded p-2 text-[10px] font-mono leading-relaxed">
              <button
                onClick={handleCopy}
                className="absolute top-1 right-1 text-[9px] px-1.5 py-0.5 rounded bg-slate-600 hover:bg-slate-500 text-slate-300"
              >
                {copiedInstruction ? 'Copied' : 'Copy'}
              </button>
              <p className="pr-12">{instructionText}</p>
            </div>
          )}

          {/* Runs list */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">Runs</p>
              <button
                onClick={loadRuns}
                disabled={loadingRuns}
                className="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 hover:bg-gray-200 text-gray-600 disabled:opacity-50"
              >
                {loadingRuns ? 'Loading...' : 'Refresh'}
              </button>
            </div>

            {!hasRuns ? (
              <p className="text-[10px] text-gray-400 italic">No temporal runs yet. Use the instruction above with Claude Code to create one.</p>
            ) : (
              <div className="space-y-0.5">
                {runs.map(run => (
                  <label
                    key={run.temporal_run_id}
                    className="flex items-center gap-1.5 text-[10px] text-gray-600 cursor-pointer hover:bg-gray-50 rounded px-1 py-0.5"
                  >
                    <input
                      type="checkbox"
                      checked={selectedRunIds.includes(run.temporal_run_id)}
                      onChange={() => toggleRunSelection(run.temporal_run_id)}
                      className="w-3 h-3"
                    />
                    <span className="font-mono">
                      {run.processing_mode}
                    </span>
                    <span className="text-gray-400">
                      {run.sequence_positions} pos
                    </span>
                    <span className="text-gray-400 truncate">
                      ({run.new_session_id.slice(0, 8)})
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Lag Chart */}
          {hasLagData && (
            <>
              <div
                ref={chartRef}
                style={{ width: '100%', height: 150 }}
              />

              {/* Scrubber */}
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <input
                    type="range"
                    min={0}
                    max={maxPosition}
                    value={scrubberPosition}
                    onChange={e => setScrubberPosition(Number(e.target.value))}
                    className="flex-1"
                  />
                  <span className="text-[10px] text-gray-500 font-mono w-16 text-right">
                    pos {scrubberPosition} / {maxPosition}
                  </span>
                </div>

                {/* Scrubber details */}
                {scrubberPoint && (
                  <div className="bg-gray-50 rounded px-2 py-1 text-[10px] text-gray-600 space-y-0.5">
                    <p className="truncate" title={scrubberSentence || ''}>
                      {scrubberSentence
                        ? (scrubberSentence.length > 80
                            ? scrubberSentence.slice(0, 80) + '...'
                            : scrubberSentence)
                        : '—'}
                    </p>
                    <div className="flex gap-3 text-gray-400">
                      <span>Regime {scrubberPoint.regime}</span>
                      <span>proj = {scrubberPoint.projection.toFixed(3)}</span>
                      <span className="font-mono">{scrubberPoint.probe_id.slice(0, 8)}</span>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Lag Metrics */}
          {hasLagData && lagMetrics.perRun && Object.keys(lagMetrics.perRun).length > 0 && (
            <div className="bg-gray-50 rounded p-2 space-y-0.5">
              <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide mb-1">Metrics</p>
              {Object.entries(lagMetrics.perRun).map(([runId, m]) => {
                const run = runs.find(r => r.temporal_run_id === runId)
                return (
                  <p key={runId} className="text-[10px] text-gray-600">
                    Routing lag ({run?.processing_mode || runId.slice(0, 6)}): <span className="font-mono font-medium">{m.lag} positions</span>
                  </p>
                )
              })}
              {lagMetrics.deltaPersistence !== null && (
                <p className="text-[10px] text-gray-700 font-medium mt-1">
                  {'\u0394'}Persistence: <span className="font-mono">{lagMetrics.deltaPersistence > 0 ? '+' : ''}{lagMetrics.deltaPersistence}</span>
                  <span className="text-gray-400 font-normal ml-1">
                    (cache {lagMetrics.deltaPersistence > 0 ? 'extends' : 'reduces'} regime by {Math.abs(lagMetrics.deltaPersistence)} steps)
                  </span>
                </p>
              )}
              {/* Basin separation from first available run */}
              {(() => {
                const firstLag = Object.values(lagDataMap).find(Boolean)
                if (!firstLag) return null
                return (
                  <p className="text-[10px] text-gray-400">
                    Basin separation: {firstLag.basin_separation.toFixed(1)} (L2 centroid distance)
                  </p>
                )
              })()}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
