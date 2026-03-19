import React, { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import 'echarts-gl'
import type { ReductionPoint } from '../../types/api'
import type { GradientScheme } from '../../utils/colorBlending'
import { getNodeColor } from '../../utils/colorBlending'
import { apiClient } from '../../api/client'

interface Trajectory {
  probe_id: string
  target: string
  label?: string
  coordinates: Array<{ layer: number; dims: number[] }>
}

interface SteppedTrajectoryPlotProps {
  sessionIds: string[]
  layers: number[]
  colorLabelA: string
  colorLabelB: string
  gradient?: GradientScheme
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
}

export default function SteppedTrajectoryPlot({
  sessionIds,
  layers,
  colorLabelA,
  colorLabelB,
  gradient = 'red-blue',
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
  nComponents = 3
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
  }, [sessionIds, layers, maxTrajectories, manualTrigger, source, method, nComponents])

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
  }, [trajectories, colorLabelA, colorLabelB, gradient, layerOffset, showLines, coordScale, xDim, yDim, zDim])

  const loadTrajectoryData = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await apiClient.reduce({
        session_ids: sessionIds,
        layers,
        source,
        method,
        n_components: nComponents
      })

      // Transform flat ReductionPoint[] into trajectory groups
      const trajectoryMap = new Map<string, ReductionPoint[]>()
      for (const point of response.points) {
        if (!trajectoryMap.has(point.probe_id)) trajectoryMap.set(point.probe_id, [])
        trajectoryMap.get(point.probe_id)!.push(point)
      }

      const probeIds = Array.from(trajectoryMap.keys()).slice(0, maxTrajectories)
      const built: Trajectory[] = probeIds.map(probeId => {
        const points = trajectoryMap.get(probeId)!.sort((a, b) => a.layer - b.layer)
        return {
          probe_id: probeId,
          target: points[0]?.target_word || '',
          label: points[0]?.label,
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

  const getTrajectoryColor = (trajectory: Trajectory) => {
    if (trajectory.label) {
      const dist = { [trajectory.label]: 1 }
      return getNodeColor(dist, colorLabelA, colorLabelB, undefined, undefined, gradient)
    }
    return '#666666'
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

    // Group trajectories by label
    const categoryGroups = new Map<string, Trajectory[]>()

    trajectories.forEach((trajectory) => {
      const groupKey = trajectory.label || 'Unknown'
      if (!categoryGroups.has(groupKey)) {
        categoryGroups.set(groupKey, [])
      }
      categoryGroups.get(groupKey)!.push(trajectory)
    })

    const series: any[] = []

    categoryGroups.forEach((groupTrajectories, groupName) => {
      const scatterData: any[] = []

      groupTrajectories.forEach((trajectory) => {
        const trajectoryColor = getTrajectoryColor(trajectory)

        trajectory.coordinates.forEach((coord) => {
          const layerIndex = actualLayers.indexOf(coord.layer)
          const xOffset = layerIndex * layerOffsetStep

          scatterData.push([
            (coord.dims[xDim] || 0) * coordScale + xOffset,
            (coord.dims[yDim] || 0) * coordScale,
            (coord.dims[zDim] || 0) * coordScale,
            trajectory.target,
            trajectory.label || '',
            trajectory.probe_id
          ])
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
              opacity: 0.7
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

      const firstTrajectory = groupTrajectories[0]
      const categoryColor = getTrajectoryColor(firstTrajectory)

      series.push({
        type: 'scatter3D',
        coordinateSystem: 'cartesian3D',
        name: `${groupName} (${groupTrajectories.length})`,
        data: scatterData,
        itemStyle: {
          color: categoryColor,
          opacity: 0.8
        },
        symbol: 'circle',
        symbolSize: 4,
        tooltip: {
          formatter: (params: any) => {
            const [x, y, , target, label] = params.data
            return `
              <strong>${target}</strong><br/>
              Label: ${label}<br/>
              Group: ${groupName}<br/>
              Coords: (${x.toFixed(3)}, ${y.toFixed(3)})<br/>
              <em>Click for sentence</em>
            `
          }
        }
      })
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
        text: `Stepped ${methodLabel} Trajectories — ${colorLabelA} vs ${colorLabelB}`,
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
      if (params.seriesType === 'scatter3D' && onPointClickRef.current && params.data) {
        const [, , , target, label, probeId] = params.data
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
          )).sort((a, b) => a - b).join('→')} • Colored by {colorLabelA} vs {colorLabelB}
        </div>
      )}
    </div>
  )
}
