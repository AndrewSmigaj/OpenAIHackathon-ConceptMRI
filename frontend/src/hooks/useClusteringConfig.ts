import { useState } from 'react'

export interface ClusteringConfigState {
  layerClusterCounts: Record<number, number>
  clusteringMethod: string
  reductionDims: number
  embeddingSource: string
  reductionMethod: string
  useAllLayersSameClusters: boolean
  globalClusterCount: number
  clusteringDimSubset: number[] | null
  clusterDimInput: string
  setLayerClusterCounts: React.Dispatch<React.SetStateAction<Record<number, number>>>
  setClusteringMethod: React.Dispatch<React.SetStateAction<string>>
  setReductionDims: React.Dispatch<React.SetStateAction<number>>
  setEmbeddingSource: React.Dispatch<React.SetStateAction<string>>
  setReductionMethod: React.Dispatch<React.SetStateAction<string>>
  setUseAllLayersSameClusters: React.Dispatch<React.SetStateAction<boolean>>
  setGlobalClusterCount: React.Dispatch<React.SetStateAction<number>>
  setClusteringDimSubset: React.Dispatch<React.SetStateAction<number[] | null>>
  setClusterDimInput: React.Dispatch<React.SetStateAction<string>>
}

export function useClusteringConfig(): ClusteringConfigState {
  const [layerClusterCounts, setLayerClusterCounts] = useState<Record<number, number>>({})
  const [clusteringMethod, setClusteringMethod] = useState('hierarchical')
  const [reductionDims, setReductionDims] = useState(5)
  const [embeddingSource, setEmbeddingSource] = useState<string>('residual_stream')
  const [reductionMethod, setReductionMethod] = useState<string>('umap')
  const [useAllLayersSameClusters, setUseAllLayersSameClusters] = useState(true)
  const [globalClusterCount, setGlobalClusterCount] = useState(6)
  const [clusteringDimSubset, setClusteringDimSubset] = useState<number[] | null>(null)
  const [clusterDimInput, setClusterDimInput] = useState('all')

  return {
    layerClusterCounts, clusteringMethod, reductionDims, embeddingSource,
    reductionMethod, useAllLayersSameClusters, globalClusterCount,
    clusteringDimSubset, clusterDimInput,
    setLayerClusterCounts, setClusteringMethod, setReductionDims, setEmbeddingSource,
    setReductionMethod, setUseAllLayersSameClusters, setGlobalClusterCount,
    setClusteringDimSubset, setClusterDimInput,
  }
}
