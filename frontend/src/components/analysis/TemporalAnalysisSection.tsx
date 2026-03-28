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
    runGroups,
    aggregateLines,
    highlightedRunId, setHighlightedRunId,
    showAggregate, setShowAggregate,
    toggleGroupSelection,
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

    // Build series — three tiers: individual (dim), highlighted, aggregate
    const series: any[] = []
    let regimeBoundary = 0
    let isFirstSeries = true

    for (const group of runGroups) {
      for (const run of group.runs) {
        const runId = run.temporal_run_id
        if (!selectedRunIds.includes(runId)) continue

        const lagData = lagDataMap[runId]
        if (!lagData) continue

        regimeBoundary = lagData.regime_boundary
        const isHighlighted = runId === highlightedRunId

        const data = lagData.points
          .sort((a, b) => a.position - b.position)
          .map(p => [p.position, p.projection])

        series.push({
          name: group.label,
          type: 'line',
          data,
          smooth: false,
          symbol: isHighlighted ? 'circle' : 'none',
          symbolSize: isHighlighted ? 4 : 0,
          lineStyle: {
            width: isHighlighted ? 2.5 : 1,
            color: group.color,
            opacity: isHighlighted ? 1.0 : 0.25,
          },
          itemStyle: {
            color: group.color,
            opacity: isHighlighted ? 1.0 : 0.25,
          },
          z: isHighlighted ? 5 : 1,
          // Mark lines only on first series
          markLine: isFirstSeries ? {
            silent: true,
            symbol: 'none',
            data: [
              { xAxis: regimeBoundary, lineStyle: { type: 'dashed', color: '#ef4444', width: 1.5 }, label: { formatter: 'regime boundary', fontSize: 9, color: '#ef4444' } },
              { yAxis: 0, lineStyle: { type: 'dotted', color: '#6b7280', width: 1 }, label: { formatter: 'basin A (0)', fontSize: 8, color: '#6b7280', position: 'insideEndTop' } },
              { yAxis: 1, lineStyle: { type: 'dotted', color: '#6b7280', width: 1 }, label: { formatter: 'basin B (1)', fontSize: 8, color: '#6b7280', position: 'insideEndTop' } },
            ],
          } : undefined,
        })
        isFirstSeries = false
      }

      // Add aggregate line for this group if enabled and available
      if (showAggregate && aggregateLines[group.key]) {
        const agg = aggregateLines[group.key]
        const data = agg.positions.map((pos, i) => [pos, agg.meanProjection[i]])

        series.push({
          name: `${group.label} (mean)`,
          type: 'line',
          data,
          smooth: false,
          symbol: 'diamond',
          symbolSize: 5,
          lineStyle: {
            width: 3,
            color: group.color,
            type: 'dashed',
            opacity: 0.9,
          },
          itemStyle: {
            color: group.color,
            opacity: 0.9,
          },
          z: 8,
        })
      }
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

    // Only show one legend entry per group (not per individual run)
    const legendData = runGroups
      .filter(g => g.runs.some(r => selectedRunIds.includes(r.temporal_run_id)))
      .flatMap(g => {
        const entries = [g.label]
        if (showAggregate && aggregateLines[g.key]) entries.push(`${g.label} (mean)`)
        return entries
      })

    const option: echarts.EChartsOption = {
      animation: false,
      legend: {
        show: true,
        data: legendData,
        bottom: 0,
        left: 'center',
        orient: 'horizontal',
        textStyle: { fontSize: 10 },
        itemWidth: 16,
        itemHeight: 8,
        itemGap: 20,
      },
      grid: { left: 50, right: 20, top: 10, bottom: 45 },
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
        min: -0.7,
        max: 1.6,
        splitLine: { lineStyle: { type: 'dashed', color: '#e5e7eb' } },
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (Array.isArray(params)) return ''
          const [pos, proj] = params.data
          return `${params.seriesName}<br/>pos ${pos}<br/>projection: ${proj?.toFixed(3)}`
        },
      },
      series,
    }

    if (series.length === 0) {
      chart.clear()
      return
    }

    chart.setOption(option, true)

    return () => {}
  }, [selectedRunIds, lagDataMap, runs, scrubberPoint, maxPosition, runGroups, highlightedRunId, showAggregate, aggregateLines])

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

  // Sentence text at scrubber position
  const scrubberSentence = scrubberPoint?.sentence_text || null

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

          {/* Runs list — grouped by condition */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">Runs</p>
              <div className="flex items-center gap-2">
                {hasLagData && (
                  <label className="flex items-center gap-1 text-[9px] text-gray-500 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showAggregate}
                      onChange={() => setShowAggregate(!showAggregate)}
                      className="w-2.5 h-2.5"
                    />
                    Mean
                  </label>
                )}
                <button
                  onClick={loadRuns}
                  disabled={loadingRuns}
                  className="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 hover:bg-gray-200 text-gray-600 disabled:opacity-50"
                >
                  {loadingRuns ? 'Loading...' : 'Refresh'}
                </button>
              </div>
            </div>

            {!hasRuns ? (
              <p className="text-[10px] text-gray-400 italic">No temporal runs yet. Use the instruction above with Claude Code to create one.</p>
            ) : runGroups.length === 0 ? (
              <p className="text-[10px] text-gray-400 italic">No runs found.</p>
            ) : (
              <div className="space-y-1.5">
                {runGroups.map(group => {
                  const groupIds = group.runs.map(r => r.temporal_run_id)
                  const allSelected = groupIds.every(id => selectedRunIds.includes(id))
                  const someSelected = groupIds.some(id => selectedRunIds.includes(id))

                  return (
                    <div key={group.key}>
                      {/* Group header */}
                      <div className="flex items-center gap-1.5 text-[10px]">
                        <input
                          type="checkbox"
                          checked={allSelected}
                          ref={el => { if (el) el.indeterminate = someSelected && !allSelected }}
                          onChange={() => toggleGroupSelection(group)}
                          className="w-3 h-3"
                        />
                        <span
                          className="w-2 h-2 rounded-full inline-block"
                          style={{ backgroundColor: group.color }}
                        />
                        <span className="font-medium text-gray-700">{group.label}</span>
                        <span
                          className="text-[8px] px-1 py-0.5 rounded font-mono font-semibold"
                          style={{ backgroundColor: group.color + '20', color: group.color }}
                        >
                          {group.runs[0]?.processing_mode?.includes('cache_on') ? 'CACHE ON' : 'CACHE OFF'}
                        </span>
                        <span className="text-gray-400">({group.runs.length} run{group.runs.length !== 1 ? 's' : ''})</span>
                      </div>

                      {/* Individual runs */}
                      <div className="ml-4 space-y-0">
                        {group.runs.map((run, idx) => {
                          const isHighlighted = run.temporal_run_id === highlightedRunId
                          const schema = run.clustering_schema || 'default'
                          const tooltipText = `${run.temporal_run_id}\nsession: ${run.new_session_id}\nschema: ${schema}\nmode: ${run.processing_mode}\nconfig: ${run.sequence_config}\npositions: ${run.sequence_positions}\nboundary: ${run.regime_boundary}`

                          return (
                            <label
                              key={run.temporal_run_id}
                              className={`flex items-center gap-1.5 text-[10px] cursor-pointer rounded px-1 py-0.5 ${
                                isHighlighted ? 'bg-blue-50 font-medium' : 'hover:bg-gray-50'
                              }`}
                              title={tooltipText}
                            >
                              <input
                                type="checkbox"
                                checked={selectedRunIds.includes(run.temporal_run_id)}
                                onChange={() => toggleRunSelection(run.temporal_run_id)}
                                className="w-2.5 h-2.5"
                              />
                              <span
                                className="text-gray-600 cursor-pointer"
                                onClick={(e) => {
                                  e.preventDefault()
                                  setHighlightedRunId(isHighlighted ? null : run.temporal_run_id)
                                }}
                              >
                                #{idx + 1}
                              </span>
                              <span className="text-gray-400 truncate">
                                ({run.new_session_id.slice(0, 8)})
                              </span>
                            </label>
                          )
                        })}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Lag Chart */}
          {hasLagData && (
            <>
              <div
                ref={chartRef}
                style={{ width: '100%', minWidth: 1400, height: 540 }}
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

          {/* Lag Metrics — per group aggregation */}
          {hasLagData && lagMetrics.perGroup && Object.keys(lagMetrics.perGroup).length > 0 && (
            <div className="bg-gray-50 rounded p-2 space-y-0.5">
              <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide mb-1">Metrics</p>
              {runGroups.map(group => {
                const gm = lagMetrics.perGroup[group.key]
                if (!gm) return null
                return (
                  <p key={group.key} className="text-[10px] text-gray-600">
                    <span className="inline-block w-2 h-2 rounded-full mr-1" style={{ backgroundColor: group.color }} />
                    {group.label}: lag = <span className="font-mono font-medium">
                      {gm.count > 1 ? `${gm.meanLag.toFixed(1)} ± ${gm.stdLag.toFixed(1)}` : gm.meanLag}
                    </span>
                    <span className="text-gray-400 ml-1">(n={gm.count})</span>
                  </p>
                )
              })}
              {lagMetrics.deltaPersistence !== null && (
                <p className="text-[10px] text-gray-700 font-medium mt-1">
                  {'\u0394'}Persistence: <span className="font-mono">{lagMetrics.deltaPersistence > 0 ? '+' : ''}{lagMetrics.deltaPersistence.toFixed(1)}</span>
                  <span className="text-gray-400 font-normal ml-1">
                    (cache {lagMetrics.deltaPersistence > 0 ? 'extends' : 'reduces'} regime by {Math.abs(lagMetrics.deltaPersistence).toFixed(1)} steps)
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
