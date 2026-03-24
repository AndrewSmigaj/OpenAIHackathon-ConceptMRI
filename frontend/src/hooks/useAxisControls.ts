import { useState, useMemo } from 'react'
import type { DynamicAxis } from '../types/api'
import type { GradientScheme } from '../utils/colorBlending'
import { GRADIENT_AUTO_PAIRS } from '../utils/colorBlending'

export interface AxisControlsState {
  // Input axes
  allAxes: DynamicAxis[]
  colorAxisId: string
  colorAxis2Id: string
  shapeAxisId: string
  gradient: GradientScheme
  selectedRange: string
  // Output axes
  outputAxes: DynamicAxis[]
  outputColorAxisId: string
  outputColorAxis2Id: string
  outputGradient: GradientScheme
  // Derived values
  colorAxis: DynamicAxis | undefined
  colorAxis2: DynamicAxis | undefined
  shapeAxis: DynamicAxis | undefined
  secondaryGradient: GradientScheme
  primaryValues: string[]
  secondaryValues: string[] | undefined
  outputColorAxis: DynamicAxis | undefined
  outputColorAxis2: DynamicAxis | undefined
  outputSecondaryGradient: GradientScheme
  outputPrimaryValues: string[]
  outputSecondaryValues: string[] | undefined
  outputGroupingAxes: string[] | undefined
  // Setters
  setAllAxes: React.Dispatch<React.SetStateAction<DynamicAxis[]>>
  setColorAxisId: React.Dispatch<React.SetStateAction<string>>
  setColorAxis2Id: React.Dispatch<React.SetStateAction<string>>
  setShapeAxisId: React.Dispatch<React.SetStateAction<string>>
  setGradient: React.Dispatch<React.SetStateAction<GradientScheme>>
  setSelectedRange: React.Dispatch<React.SetStateAction<string>>
  setOutputAxes: React.Dispatch<React.SetStateAction<DynamicAxis[]>>
  setOutputColorAxisId: React.Dispatch<React.SetStateAction<string>>
  setOutputColorAxis2Id: React.Dispatch<React.SetStateAction<string>>
  setOutputGradient: React.Dispatch<React.SetStateAction<GradientScheme>>
}

export function useAxisControls(): AxisControlsState {
  const [allAxes, setAllAxes] = useState<DynamicAxis[]>([])
  const [colorAxisId, setColorAxisId] = useState<string>('label')
  const [colorAxis2Id, setColorAxis2Id] = useState<string>('none')
  const [shapeAxisId, setShapeAxisId] = useState<string>('none')
  const [gradient, setGradient] = useState<GradientScheme>('red-blue')
  const [selectedRange, setSelectedRange] = useState<string>('range1')

  const [outputAxes, setOutputAxes] = useState<DynamicAxis[]>([])
  const [outputColorAxisId, setOutputColorAxisId] = useState<string>('')
  const [outputColorAxis2Id, setOutputColorAxis2Id] = useState<string>('none')
  const [outputGradient, setOutputGradient] = useState<GradientScheme>('purple-green')

  const colorAxis = allAxes.find(a => a.id === colorAxisId)
  const colorAxis2 = allAxes.find(a => a.id === colorAxis2Id)
  const shapeAxis = allAxes.find(a => a.id === shapeAxisId)
  const secondaryGradient = GRADIENT_AUTO_PAIRS[gradient]

  const primaryValues = useMemo(() =>
    colorAxis?.values || (colorAxis ? [colorAxis.label_a, colorAxis.label_b] : []),
    [colorAxis]
  )
  const secondaryValues = useMemo(() =>
    colorAxis2?.values || (colorAxis2 ? [colorAxis2.label_a, colorAxis2.label_b] : undefined),
    [colorAxis2]
  )

  const outputColorAxis = outputAxes.find(a => a.id === outputColorAxisId)
  const outputColorAxis2 = outputAxes.find(a => a.id === outputColorAxis2Id)
  const outputSecondaryGradient = GRADIENT_AUTO_PAIRS[outputGradient]
  const outputPrimaryValues = useMemo(() =>
    outputColorAxis?.values || (outputColorAxis ? [outputColorAxis.label_a, outputColorAxis.label_b] : []),
    [outputColorAxis]
  )
  const outputSecondaryValues = useMemo(() =>
    outputColorAxis2?.values || (outputColorAxis2 ? [outputColorAxis2.label_a, outputColorAxis2.label_b] : undefined),
    [outputColorAxis2]
  )

  const outputGroupingAxes = useMemo(() => {
    const axes: string[] = []
    if (outputColorAxisId && outputColorAxisId !== 'none') axes.push(outputColorAxisId)
    if (outputColorAxis2Id && outputColorAxis2Id !== 'none') axes.push(outputColorAxis2Id)
    return axes.length > 0 ? axes : undefined
  }, [outputColorAxisId, outputColorAxis2Id])

  return {
    allAxes, colorAxisId, colorAxis2Id, shapeAxisId, gradient, selectedRange,
    outputAxes, outputColorAxisId, outputColorAxis2Id, outputGradient,
    colorAxis, colorAxis2, shapeAxis, secondaryGradient,
    primaryValues, secondaryValues,
    outputColorAxis, outputColorAxis2, outputSecondaryGradient,
    outputPrimaryValues, outputSecondaryValues, outputGroupingAxes,
    setAllAxes, setColorAxisId, setColorAxis2Id, setShapeAxisId, setGradient, setSelectedRange,
    setOutputAxes, setOutputColorAxisId, setOutputColorAxis2Id, setOutputGradient,
  }
}
