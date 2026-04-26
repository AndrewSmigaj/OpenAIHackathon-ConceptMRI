import type { ClusteringSchema } from '../../types/api'

interface Props {
  schema: ClusteringSchema | undefined
}

// Color groups: parameters that belong to the same axis share a color.
//   - Clustering (method + K): indigo
//   - Reduction (method + dim + n_neighbors): violet
//   - Embedding source: blue
//   - Filter info (steps, last_occurrence, sample size): slate
const TAG_BASE: React.CSSProperties = {
  padding: '1px 6px',
  borderRadius: 4,
  fontWeight: 500,
  display: 'inline-block',
}
const TAG_CLUSTERING: React.CSSProperties = { ...TAG_BASE, background: '#e0e7ff', color: '#3730a3' }
const TAG_REDUCTION:  React.CSSProperties = { ...TAG_BASE, background: '#ede9fe', color: '#5b21b6' }
const TAG_EMBEDDING:  React.CSSProperties = { ...TAG_BASE, background: '#dbeafe', color: '#1e40af' }
const TAG_FILTER:     React.CSSProperties = { ...TAG_BASE, background: '#f1f5f9', color: '#334155', fontWeight: 400 }

function formatStepClause(steps: number[] | undefined): string {
  if (!steps || steps.length === 0) return ''
  if (steps.length === 1) return `step ${steps[0]}`
  if (steps.length === 2) return `steps ${steps[0]} and ${steps[1]}`
  return `steps ${steps.slice(0, -1).join(', ')}, and ${steps[steps.length - 1]}`
}

function formatClusteringMethod(method: string): string {
  switch (method) {
    case 'hierarchical': return 'hierarchical'
    case 'kmeans':       return 'k-means'
    case 'dbscan':       return 'DBSCAN'
    default:             return method
  }
}

function formatEmbeddingSource(source: string): string {
  switch (source) {
    case 'residual_stream': return 'residual stream'
    case 'expert_output':   return 'expert output'
    default:                return source.replace(/_/g, ' ')
  }
}

function clusterCount(layerCounts: Record<string, number> | undefined, nClusters: number | undefined): string {
  if (layerCounts && Object.keys(layerCounts).length > 0) {
    const values = Object.values(layerCounts)
    const min = Math.min(...values)
    const max = Math.max(...values)
    return min === max ? `${min}` : `${min}–${max}`
  }
  return nClusters !== undefined ? `${nClusters}` : '?'
}

export default function SchemaSummary({ schema }: Props) {
  if (!schema) return null
  const { params } = schema
  const sampleSize = schema.sample_size ?? 0
  const stepClause = formatStepClause(schema.steps)
  const lastOcc    = schema.last_occurrence_only
  const isCapped   = schema.max_probes != null && schema.sample_size != null && schema.sample_size === schema.max_probes

  const k          = clusterCount(params.layer_cluster_counts, params.n_clusters)
  const method     = formatClusteringMethod(params.clustering_method)
  const reduction  = (params.reduction_method || '').toUpperCase()
  const dim        = params.reduction_dimensions
  const nNeighbors = params.n_neighbors
  const embedding  = formatEmbeddingSource(params.embedding_source)
  const isUmap     = params.reduction_method === 'umap'

  const filterText = [stepClause, lastOcc ? 'last-occurrence' : ''].filter(Boolean).join(', ')

  return (
    <div style={{ fontSize: '11px', color: '#334155', lineHeight: 1.6 }}>
      <div style={{ fontFamily: 'monospace', fontSize: '10.5px', color: '#64748b', marginBottom: 2 }}>
        {schema.name}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', columnGap: 4, rowGap: 4 }}>
        <span>{sampleSize.toLocaleString()} probes</span>
        {filterText && <span style={TAG_FILTER}>{filterText}</span>}
        {isCapped && <span style={TAG_FILTER}>capped at {schema.max_probes}</span>}
        <span>·</span>
        <span style={TAG_CLUSTERING}>{k} {method} clusters/layer</span>
        <span>over</span>
        <span style={TAG_REDUCTION}>
          {reduction} {dim}D{isUmap && nNeighbors != null ? `, n=${nNeighbors}` : ''}
        </span>
        <span>of</span>
        <span style={TAG_EMBEDDING}>{embedding}</span>
        <span>activations.</span>
      </div>
    </div>
  )
}
