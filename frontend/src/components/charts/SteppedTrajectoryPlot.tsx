import React, { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import 'echarts-gl'
import type { ReductionPoint } from '../../types/api'
import type { GradientScheme } from '../../utils/colorBlending'
import { getPointColor } from '../../utils/colorBlending'
import { apiClient } from '../../api/client'

interface Trajectory {
  probe_id: string
  target: string
  label?: string
  categories?: Record<string, string>
  coordinates: Array<{ layer: number; dims: number[] }>
  step?: number
}

const SHAPE_SYMBOLS = ['circle', 'triangle', 'diamond', 'rect', 'pin', 'arrow']

interface SteppedTrajectoryPlotProps {
  sessionIds: string[]
  layers: number[]
  colorLabelA: string
  colorLabelB: string
  gradient?: GradientScheme
  primaryValues?: string[]
  secondaryColorAxisId?: string
  secondaryValues?: string[]
  shapeAxisId?: string
  shapeValues?: string[]
  source?: string        // "expert_output" | "residual_stream"
  method?: string        // "pca" | "umap"
  sessionData?: any
  filterConfig?: any
  className?: string
  height?: number
  maxTrajectories?: number
  manualTrigger?: boolean
  onAnalysisReady?: (runAnalysis: () => void) => void
  onPointClick?: (info: { probe_id: string; target: string; label?: string }) => void
  nComponents?: number
  steps?: number[] | null
  lastOccurrenceOnly?: boolean
  maxProbes?: number | null
  nNeighbors?: number
  selectedProbeId?: string | null
}

export default function SteppedTrajectoryPlot({
  sessionIds,
  layers,
  colorLabelA,
  colorLabelB,
  gradient = 'red-blue',
  primaryValues,
  secondaryColorAxisId,
  secondaryValues,
  shapeAxisId,
  shapeValues,
  source = 'expert_output',
  method = 'pca',
  sessionData,
  filterConfig,
  className = '',
  height = 400,
  maxTrajectories = 200,
  manualTrigger = false,
  onAnalysisReady,
  onPointClick,
  nComponents = 3,
  steps,
  lastOccurrenceOnly,
  maxProbes,
  nNeighbors,
  selectedProbeId
}: SteppedTrajectoryPlotProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<echarts.ECharts | null>(null)
  const onPointClickRef = useRef(onPointClick)
  onPointClickRef.current = onPointClick
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [trajectories, setTrajectories] = useState<Trajectory[]>([])
  const [layerOffset, setLayerOffset] = useState(72)
  const [showLines, setShowLines] = useState(true)
  const [pointSize, setPointSize] = useState(2)
  const [coordScale, setCoordScale] = useState(1)
  const [xDim, setXDim] = useState(0)
  const [yDim, setYDim] = useState(1)
  const [zDim, setZDim] = useState(2)

  useEffect(() => {
    if (manualTrigger) {
      if (onAnalysisReady) {
        onAnalysisReady(() => {
          if (sessionIds.length > 0 && layers.length >= 2) {
            loadTrajectoryData()
          }
        })
      }
      return
    }

    if (!sessionIds.length || layers.length < 2) return

    loadTrajectoryData()
  }, [sessionIds, layers, manualTrigger, source, method, nComponents, steps, lastOccurrenceOnly, maxProbes, nNeighbors, onAnalysisReady])

  useEffect(() => {
    if (trajectories.length > 0 && chartRef.current) {
      initializeChart()
    }

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.dispose()
        chartInstanceRef.current = null
      }
    }
  }, [trajectories, colorLabelA, colorLabelB, gradient, primaryValues, secondaryColorAxisId, secondaryValues, shapeAxisId, shapeValues, layerOffset, showLines, pointSize, coordScale, xDim, yDim, zDim, selectedProbeId])

  const loadTrajectoryData = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await apiClient.reduce({
        session_ids: sessionIds,
        layers,
        source,
        method,
        n_components: nComponents,
        ...(steps ? { steps } : {}),
        ...(lastOccurrenceOnly ? { last_occurrence_only: true } : {}),
        ...(maxProbes != null ? { max_probes: maxProbes } : {}),
        ...(nNeighbors != null ? { n_neighbors: nNeighbors } : {})
      })

      // Transform flat ReductionPoint[] into trajectory groups
      const trajectoryMap = new Map<string, ReductionPoint[]>()
      for (const point of response.points) {
        if (!trajectoryMap.has(point.probe_id)) trajectoryMap.set(point.probe_id, [])
        trajectoryMap.get(point.probe_id)!.push(point)
      }

      // Backend already applied max_probes subsampling (if set). Render every
      // probe the backend returned, up to maxTrajectories as a safety ceiling
      // for accidental unbounded fetches.
      let probeIds = Array.from(trajectoryMap.keys())
      if (probeIds.length > maxTrajectories) {
        probeIds.sort()
        probeIds = probeIds.slice(0, maxTrajectories)
      }
      const built: Trajectory[] = probeIds.map(probeId => {
        const points = trajectoryMap.get(probeId)!.sort((a, b) => a.layer - b.layer)
        return {
          probe_id: probeId,
          target: points[0]?.target_word || '',
          label: points[0]?.label,
          categories: points[0]?.categories,
          step: points[0]?.step,
          coordinates: points.map(p => ({
            layer: p.layer,
            dims: p.coordinates ?? [p.x, p.y ?? 0, p.z ?? 0]
          }))
        }
      })

      setTrajectories(built)
    } catch (err) {
      console.error('Failed to load trajectory data:', err)
      setError(err instanceof Error ? err.message : 'Failed to load trajectory data')
    } finally {
      setLoading(false)
    }
  }

  const getAxisValue = (t: Trajectory, axisId?: string): string | undefined => {
    if (!axisId) return undefined
    if (axisId === 'label') return t.label
    if (axisId === 'target_word') return t.target
    return t.categories?.[axisId]
  }

  const getTrajectoryColor = (trajectory: Trajectory) => {
    const primaryValue = getAxisValue(trajectory, 'label')
    if (!primaryValue) return '#666666'
    const effectivePrimaryValues = primaryValues || [colorLabelA, colorLabelB].filter(Boolean)
    const secValue = secondaryColorAxisId ? getAxisValue(trajectory, secondaryColorAxisId) : undefined
    return getPointColor(primaryValue, effectivePrimaryValues, gradient, secValue, secondaryValues)
  }

  const initializeChart = () => {
    if (!chartRef.current || trajectories.length === 0) return

    if (chartInstanceRef.current) {
      chartInstanceRef.current.dispose()
    }

    const chart = echarts.init(chartRef.current)
    chartInstanceRef.current = chart

    const layerOffsetStep = layerOffset

    const actualLayers = Array.from(new Set(
      trajectories.flatMap(t => t.coordinates.map(c => c.layer))
    )).sort((a, b) => a - b)

    // Cross-product grouping: (colorGroup, shapeGroup) → separate series
    const crossGroups = new Map<string, { trajectories: Trajectory[]; colorKey: string; shapeKey: string }>()

    trajectories.forEach((trajectory) => {
      const colorKey = trajectory.label || 'Unknown'
      const shapeKey = shapeAxisId ? (getAxisValue(trajectory, shapeAxisId) || 'Unknown') : '_none'
      const groupKey = `${colorKey}|${shapeKey}`
      if (!crossGroups.has(groupKey)) {
        crossGroups.set(groupKey, { trajectories: [], colorKey, shapeKey })
      }
      crossGroups.get(groupKey)!.trajectories.push(trajectory)
    })

    const series: any[] = []
    const allScatterData: any[] = []
    const legendNames: string[] = []

    crossGroups.forEach(({ trajectories: groupTrajectories, colorKey, shapeKey }) => {
      const shapeIndex = shapeValues ? shapeValues.indexOf(shapeKey) : -1
      const symbol = shapeIndex >= 0 ? SHAPE_SYMBOLS[shapeIndex % SHAPE_SYMBOLS.length] : 'circle'
      const effectivePrimaryValues = primaryValues || [colorLabelA, colorLabelB].filter(Boolean)
      const groupColor = colorKey
        ? getPointColor(colorKey, effectivePrimaryValues, gradient)
        : '#666666'
      const legendName = shapeAxisId && shapeKey !== '_none'
        ? `${colorKey} · ${shapeKey} (${groupTrajectories.length})`
        : `${colorKey} (${groupTrajectories.length})`

      legendNames.push(legendName)

      groupTrajectories.forEach((trajectory) => {
        const trajectoryColor = getTrajectoryColor(trajectory)
        const isSelected = !selectedProbeId || trajectory.probe_id === selectedProbeId
        const pointOpacity = isSelected ? 0.95 : 0.1
        const lineOpacity = isSelected ? 0.9 : 0.08

        trajectory.coordinates.forEach((coord) => {
          const layerIndex = actualLayers.indexOf(coord.layer)
          const xOffset = layerIndex * layerOffsetStep

          allScatterData.push({
            value: [
              (coord.dims[xDim] || 0) * coordScale + xOffset,
              (coord.dims[yDim] || 0) * coordScale,
              (coord.dims[zDim] || 0) * coordScale,
              trajectory.target,
              trajectory.label || '',
              trajectory.probe_id
            ],
            itemStyle: { color: trajectoryColor, opacity: pointOpacity },
            symbol: symbol,
            symbolSize: pointSize,
          })
        })

        if (showLines && trajectory.coordinates.length > 1) {
          const trajectoryLineData = trajectory.coordinates.map((coord) => {
            const layerIndex = actualLayers.indexOf(coord.layer)
            const xOffset = layerIndex * layerOffsetStep
            return [(coord.dims[xDim] || 0) * coordScale + xOffset, (coord.dims[yDim] || 0) * coordScale, (coord.dims[zDim] || 0) * coordScale]
          })

          series.push({
            type: 'line3D',
            data: trajectoryLineData,
            lineStyle: {
              color: trajectoryColor,
              width: 1.5,
              opacity: lineOpacity
            },
            silent: true,
            animation: false,
            legendHoverLink: false,
            emphasis: {
              disabled: true
            }
          })
        }
      })

      // Legend-only series (no data — just for legend entry)
      series.push({
        type: 'scatter3D',
        coordinateSystem: 'cartesian3D',
        name: legendName,
        data: [],
        itemStyle: { color: groupColor, opacity: 0.8 },
        symbol: symbol,
        symbolSize: pointSize,
      })
    })

    // Shuffle scatter data so neither class dominates at shared depths
    for (let i = allScatterData.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [allScatterData[i], allScatterData[j]] = [allScatterData[j], allScatterData[i]]
    }

    // Single merged scatter series — depth-sorted equally across all groups
    series.push({
      type: 'scatter3D',
      coordinateSystem: 'cartesian3D',
      data: allScatterData,
      symbolSize: pointSize,
      itemStyle: { opacity: 0.8 },
      tooltip: {
        formatter: (params: any) => {
          const [x, y, , target, label] = params.value
          return `
            <strong>${target}</strong><br/>
            Label: ${label}<br/>
            Coords: (${x.toFixed(3)}, ${y.toFixed(3)})<br/>
            <em>Click for sentence</em>
          `
        }
      }
    })

    // Add vertical layer axis lines
    actualLayers.forEach((layer, index) => {
      const xOffset = index * layerOffsetStep

      series.push({
        type: 'line3D',
        data: [
          [xOffset, 0, -10],
          [xOffset, 0, 10]
        ],
        lineStyle: {
          color: '#333333',
          width: 2,
          opacity: 0.6
        },
        silent: true,
        animation: false,
        emphasis: {
          disabled: true
        }
      })

      series.push({
        type: 'surface',
        silent: true,
        parametric: true,
        wireframe: {
          show: true,
          lineStyle: {
            color: '#e0e0e0',
            width: 1,
            opacity: 0.2
          }
        },
        itemStyle: {
          color: '#f8f8f8',
          opacity: 0.02
        },
        parametricEquation: {
          u: { min: -8, max: 8, step: 16 },
          v: { min: -8, max: 8, step: 16 },
          x: (u: number, v: number) => xOffset,
          y: (u: number, v: number) => u,
          z: (u: number, v: number) => v
        }
      })
    })

    const methodLabel = method?.toUpperCase() || 'PCA'
    const option = {
      title: {
        text: primaryValues && primaryValues.length > 2
          ? `Stepped ${methodLabel} Trajectories — ${primaryValues.length} word senses of ${trajectories[0]?.target || 'target'}`
          : `Stepped ${methodLabel} Trajectories — ${colorLabelA} vs ${colorLabelB}`,
        left: 'center',
        top: 10,
        textStyle: {
          fontSize: 14,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'item'
      },
      legend: {
        show: true,
        orient: 'vertical',
        left: 'right',
        top: 'middle',
        data: legendNames,
        textStyle: {
          fontSize: 10
        }
      },
      xAxis3D: {
        type: 'value',
        name: `Dim ${xDim + 1}`,
        nameTextStyle: { fontSize: 10 }
      },
      yAxis3D: {
        type: 'value',
        name: `Dim ${yDim + 1}`,
        nameTextStyle: { fontSize: 10 }
      },
      zAxis3D: {
        type: 'value',
        name: `Dim ${zDim + 1}`,
        nameTextStyle: { fontSize: 10 }
      },
      grid3D: {
        boxWidth: (actualLayers.length - 1) * layerOffsetStep + 200,
        boxHeight: 200,
        boxDepth: 200,
        viewControl: {
          autoRotate: false,
          distance: 300,
          alpha: 25,
          beta: 35
        },
        light: {
          main: {
            intensity: 1.0,
            shadow: true,
            shadowQuality: 'medium'
          },
          ambient: {
            intensity: 0.4
          }
        }
      },
      series: series
    }

    chart.setOption(option)

    // Click handler for trajectory points
    chart.on('click', (params: any) => {
      if (params.seriesType === 'scatter3D' && onPointClickRef.current && params.value) {
        const [, , , target, label, probeId] = params.value
        if (probeId) {
          onPointClickRef.current({ probe_id: probeId, target, label })
        }
      }
    })

    const handleResize = () => { chart.resize() }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }

  if (loading) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-sm text-gray-600">Loading trajectories...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <div className="text-center">
          <p className="text-sm text-red-600">Error: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={className}>
      <div className="mb-2 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-1">
          <label className="text-xs text-gray-500">Spacing:</label>
          <input
            type="range"
            min="20"
            max="150"
            value={layerOffset}
            onChange={(e) => setLayerOffset(Number(e.target.value))}
            className="w-20"
          />
        </div>
        <div className="flex items-center gap-1">
          <label className="text-xs text-gray-500">Scale:</label>
          <input
            type="range"
            min="0.1"
            max="2"
            step="0.1"
            value={coordScale}
            onChange={(e) => setCoordScale(Number(e.target.value))}
            className="w-20"
          />
        </div>
        <div className="flex items-center gap-1">
          <label className="text-xs text-gray-500">Points:</label>
          <input
            type="range"
            min="0"
            max="8"
            step="0.5"
            value={pointSize}
            onChange={(e) => setPointSize(Number(e.target.value))}
            className="w-20"
          />
          <span className="text-xs text-gray-400 w-4">{pointSize}</span>
        </div>
        <label className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer">
          <input
            type="checkbox"
            checked={showLines}
            onChange={(e) => setShowLines(e.target.checked)}
            className="w-3 h-3 cursor-pointer"
          />
          Lines
        </label>
        {/* Axis dimension mapping */}
        {nComponents > 3 && (
          <>
            <div className="flex items-center gap-0.5">
              <span className="text-xs text-gray-500">X:</span>
              <select value={xDim} onChange={(e) => setXDim(Number(e.target.value))} className="px-1 py-0.5 text-xs border border-gray-300 rounded">
                {Array.from({ length: nComponents }, (_, i) => <option key={i} value={i}>Dim {i + 1}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-0.5">
              <span className="text-xs text-gray-500">Y:</span>
              <select value={yDim} onChange={(e) => setYDim(Number(e.target.value))} className="px-1 py-0.5 text-xs border border-gray-300 rounded">
                {Array.from({ length: nComponents }, (_, i) => <option key={i} value={i}>Dim {i + 1}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-0.5">
              <span className="text-xs text-gray-500">Z:</span>
              <select value={zDim} onChange={(e) => setZDim(Number(e.target.value))} className="px-1 py-0.5 text-xs border border-gray-300 rounded">
                {Array.from({ length: nComponents }, (_, i) => <option key={i} value={i}>Dim {i + 1}</option>)}
              </select>
            </div>
          </>
        )}
      </div>
      <div
        ref={chartRef}
        style={{ height, width: '100%' }}
      />
      {trajectories.length > 0 && (
        <div className="mt-2 text-xs text-gray-500 text-center">
          {trajectories.length} trajectories across layers {Array.from(new Set(
            trajectories.flatMap(t => t.coordinates.map(c => c.layer))
          )).sort((a, b) => a - b).join('→')} • Colored by {primaryValues && primaryValues.length > 2
            ? primaryValues.join(', ')
            : `${colorLabelA} vs ${colorLabelB}`}
        </div>
      )}
    </div>
  )
}
