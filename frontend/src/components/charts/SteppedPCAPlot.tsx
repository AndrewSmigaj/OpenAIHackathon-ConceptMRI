import React, { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import 'echarts-gl'
import type { PCATrajectoryResponse } from '../../types/api'
import type { ColorAxis, GradientScheme } from '../../utils/colorBlending'
import { getNodeColorWithGradients } from '../../utils/colorBlending'
import { apiClient } from '../../api/client'

interface SteppedPCAPlotProps {
  sessionId: string
  layers: number[]
  primaryAxis: ColorAxis
  secondaryAxis?: ColorAxis
  primaryGradient?: GradientScheme
  secondaryGradient?: GradientScheme
  sessionData?: any // For category information
  filterConfig?: any // Filter configuration (same as route analysis)
  className?: string
  height?: number
  maxTrajectories?: number
  manualTrigger?: boolean  // If true, only loads when runAnalysis is called externally
  onAnalysisReady?: (runAnalysis: () => void) => void  // Callback to provide runAnalysis function to parent
  initialLayerOffset?: number  // Initial layer offset value
}

export default function SteppedPCAPlot({ 
  sessionId, 
  layers, 
  primaryAxis,
  secondaryAxis,
  primaryGradient = 'red-blue',
  secondaryGradient = 'yellow-cyan',
  sessionData,
  filterConfig,
  className = '', 
  height = 400,
  maxTrajectories = 200,
  manualTrigger = false,
  onAnalysisReady
}: SteppedPCAPlotProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<echarts.ECharts | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [trajectoryData, setTrajectoryData] = useState<PCATrajectoryResponse | null>(null)
  const [layerOffset, setLayerOffset] = useState(72)
  const [showLines, setShowLines] = useState(true)
  const [pcaScale, setPcaScale] = useState(1)

  useEffect(() => {
    if (manualTrigger) {
      // Provide the analysis function to parent
      if (onAnalysisReady) {
        onAnalysisReady(() => {
          if (sessionId && layers.length >= 2) {
            loadTrajectoryData()
          }
        })
      }
      return
    }

    if (!sessionId || layers.length < 2) return

    loadTrajectoryData()
  }, [sessionId, layers, maxTrajectories, manualTrigger])

  useEffect(() => {
    if (trajectoryData && chartRef.current) {
      initializeChart()
    }

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.dispose()
        chartInstanceRef.current = null
      }
    }
  }, [trajectoryData, primaryAxis, secondaryAxis, primaryGradient, secondaryGradient, layerOffset, showLines, pcaScale])

  const loadTrajectoryData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const data = await apiClient.getPCATrajectories(
        sessionId,
        layers,
        3, // Use 3D for the stepped visualization
        maxTrajectories,
        filterConfig
      )
      
      setTrajectoryData(data)
    } catch (err) {
      console.error('Failed to load PCA trajectory data:', err)
      setError(err instanceof Error ? err.message : 'Failed to load trajectory data')
    } finally {
      setLoading(false)
    }
  }

  const getTrajectoryColor = (trajectory: any) => {
    if (!sessionData?.categories?.targets) {
      return '#666666' // Default gray if no category data
    }

    // Get target categories for this trajectory
    const targetCategories = sessionData.categories.targets[trajectory.target] || []
    
    if (targetCategories.length === 0) {
      return '#cccccc' // Light gray for uncategorized
    }

    // Create category distribution (similar to Sankey nodes)
    const categoryDistribution: Record<string, number> = {}
    targetCategories.forEach(category => {
      categoryDistribution[category] = 1 / targetCategories.length
    })
    
    console.log(`🎨 Color debug for "${trajectory.target}":`, {
      targetCategories,
      categoryDistribution,
      primaryAxis,
      secondaryAxis,
      primaryGradient,
      secondaryGradient
    })
    
    // Use the same color function as Sankey charts
    const color = getNodeColorWithGradients(
      categoryDistribution,
      primaryAxis,
      secondaryAxis,
      primaryGradient,
      secondaryGradient
    )
    
    console.log(`🎨 Color result for "${trajectory.target}":`, color)
    
    return color
  }

  const initializeChart = () => {
    if (!chartRef.current || !trajectoryData) return

    // Dispose existing chart
    if (chartInstanceRef.current) {
      chartInstanceRef.current.dispose()
    }

    const chart = echarts.init(chartRef.current)
    chartInstanceRef.current = chart

    // Layer offset step size for x-axis (horizontal separation)
    const layerOffsetStep = layerOffset
    
    // Get unique layers from the actual trajectory data
    const actualLayers = Array.from(new Set(
      trajectoryData.trajectories.flatMap(t => t.coordinates.map(c => c.layer))
    )).sort((a, b) => a - b)
    
    console.log('🎯 PCA Chart Debug:', {
      actualLayers,
      trajectoryCount: trajectoryData.trajectories.length,
      firstCoords: trajectoryData.trajectories[0]?.coordinates[0]
    })
    
    // Group trajectories by category for legend
    const categoryGroups = new Map<string, any[]>()
    
    trajectoryData.trajectories.forEach((trajectory) => {
      const targetCategories = sessionData?.categories?.targets?.[trajectory.target] || []
      
      let categoryName = 'Mixed'
      if (primaryAxis === 'pos') {
        if (targetCategories.includes('verbs')) categoryName = 'Verbs'
        else if (targetCategories.includes('nouns')) categoryName = 'Nouns'
        else categoryName = 'Mixed'
      } else if (primaryAxis === 'sentiment') {
        if (targetCategories.includes('positive')) categoryName = 'Positive'
        else if (targetCategories.includes('negative')) categoryName = 'Negative'
        else categoryName = 'Mixed'
      } else if (primaryAxis === 'concreteness') {
        if (targetCategories.includes('concrete')) categoryName = 'Concrete'
        else if (targetCategories.includes('abstract')) categoryName = 'Abstract'
        else categoryName = 'Mixed'
      } else if (primaryAxis === 'action-content') {
        if (targetCategories.includes('action')) categoryName = 'Action'
        else if (targetCategories.includes('content')) categoryName = 'Content'
        else categoryName = 'Mixed'
      }
      
      if (!categoryGroups.has(categoryName)) {
        categoryGroups.set(categoryName, [])
      }
      categoryGroups.get(categoryName)!.push(trajectory)
    })

    const series: any[] = []

    // Create series for each category group
    categoryGroups.forEach((trajectories, categoryName) => {
      const scatterData: any[] = []
      
      trajectories.forEach((trajectory) => {
        const trajectoryColor = getTrajectoryColor(trajectory)
        
        // Add scatter points for this trajectory
        trajectory.coordinates.forEach((coord: any) => {
          const layerIndex = actualLayers.indexOf(coord.layer)
          const xOffset = layerIndex * layerOffsetStep
          
          scatterData.push([
            (coord.x || 0) * pcaScale + xOffset,
            (coord.y || 0) * pcaScale,
            (coord.z || 0) * pcaScale,
            trajectory.target, // Store target for tooltip
            trajectory.context
          ])
        })

        // Add each trajectory as a separate line series (if lines are enabled)
        if (showLines && trajectory.coordinates.length > 1) {
          const trajectoryLineData = trajectory.coordinates.map((coord: any) => {
            const layerIndex = actualLayers.indexOf(coord.layer)
            const xOffset = layerIndex * layerOffsetStep
            return [(coord.x || 0) * pcaScale + xOffset, (coord.y || 0) * pcaScale, (coord.z || 0) * pcaScale]
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

      // Get representative color for this category
      const firstTrajectory = trajectories[0]
      const categoryColor = getTrajectoryColor(firstTrajectory)

      // Add scatter series for this category
      series.push({
        type: 'scatter3D',
        coordinateSystem: 'cartesian3D',
        name: `${categoryName} (${trajectories.length})`,
        data: scatterData,
        itemStyle: {
          color: categoryColor,
          opacity: 0.8
        },
        symbol: 'circle',
        symbolSize: 4,
        tooltip: {
          formatter: (params: any) => {
            const [x, y, z, target, context] = params.data
            return `
              <strong>${target}</strong><br/>
              Context: ${context}<br/>
              Category: ${categoryName}<br/>
              PCA: (${x.toFixed(3)}, ${y.toFixed(3)})
            `
          }
        }
      })

    })

    // Add vertical layer axis lines
    actualLayers.forEach((layer, index) => {
      const xOffset = index * layerOffsetStep
      
      // Vertical axis line for each layer
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
      
      // Add small reference plane at base
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
          u: {
            min: -8,
            max: 8,
            step: 16
          },
          v: {
            min: -8,
            max: 8,
            step: 16
          },
          x: (u: number, v: number) => xOffset,
          y: (u: number, v: number) => u,
          z: (u: number, v: number) => v
        }
      })
    })

    const option = {
      title: {
        text: `Stepped PCA Trajectories - ${primaryAxis}${secondaryAxis ? ` × ${secondaryAxis}` : ''}`,
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
        name: 'PCA Dim 1',
        nameTextStyle: {
          fontSize: 10
        }
      },
      yAxis3D: {
        type: 'value',
        name: 'PCA Dim 2',
        nameTextStyle: {
          fontSize: 10
        }
      },
      zAxis3D: {
        type: 'value',
        name: 'PCA Dim 3',
        nameTextStyle: {
          fontSize: 10
        }
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

    // Handle resize
    const handleResize = () => {
      chart.resize()
    }
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
          <p className="text-sm text-gray-600">Loading PCA trajectories...</p>
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
      <div className="mb-4 flex flex-wrap items-center gap-6">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Layer Spacing:</label>
          <input
            type="range"
            min="20"
            max="150"
            value={layerOffset}
            onChange={(e) => setLayerOffset(Number(e.target.value))}
            className="w-32"
          />
          <span className="text-sm text-gray-700 w-8">{layerOffset}</span>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">PCA Scale:</label>
          <input
            type="range"
            min="0.1"
            max="2"
            step="0.1"
            value={pcaScale}
            onChange={(e) => setPcaScale(Number(e.target.value))}
            className="w-32"
          />
          <span className="text-sm text-gray-700 w-8">{pcaScale}</span>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="showLines"
            checked={showLines}
            onChange={(e) => setShowLines(e.target.checked)}
            className="cursor-pointer"
          />
          <label htmlFor="showLines" className="text-sm text-gray-600 cursor-pointer">Show Lines</label>
        </div>
      </div>
      <div 
        ref={chartRef} 
        style={{ height, width: '100%' }}
      />
      {trajectoryData && (
        <div className="mt-2 text-xs text-gray-500 text-center">
          {trajectoryData.trajectories.length} trajectories across layers {Array.from(new Set(
            trajectoryData.trajectories.flatMap(t => t.coordinates.map(c => c.layer))
          )).sort((a, b) => a - b).join('→')} • Colored by {primaryAxis}
        </div>
      )}
    </div>
  )
}