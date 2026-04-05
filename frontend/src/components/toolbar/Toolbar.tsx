import { useMemo } from 'react'
import type { SessionListItem, SessionDetailResponse, DynamicAxis } from '../../types/api'
import type { FilterState } from '../WordFilterPanel'
import type { GradientScheme } from '../../utils/colorBlending'
import { getAxisPreview, GRADIENT_SCHEMES, GRADIENT_AUTO_PAIRS } from '../../utils/colorBlending'
import { LAYER_RANGES } from '../../constants/layerRanges'
import type { AxisControlsState } from '../../hooks/useAxisControls'
import type { ClusteringConfigState } from '../../hooks/useClusteringConfig'
import type { SchemaManagementState } from '../../hooks/useSchemaManagement'
import type { RouteAnalysisResponse } from '../../types/api'
import type { RoomContext } from '../../types/evennia'

interface ToolbarProps {
  // Session
  sessions: SessionListItem[]
  selectedSession: string
  onSessionChange: (sessionId: string) => void
  sessionDetails: SessionDetailResponse | null

  // Axes (from useAxisControls)
  axes: AxisControlsState

  // Expert route controls
  topRoutes: number
  showAllRoutes: boolean
  onTopRoutesChange: (n: number) => void
  onShowAllRoutesChange: (show: boolean) => void

  // Clustering (from useClusteringConfig)
  clustering: ClusteringConfigState

  // Schema (from useSchemaManagement)
  schema: SchemaManagementState
  selectedRange: string

  // Filters
  filterState: FilterState
  onFilterStateChange: (state: FilterState) => void
  currentRouteData: Record<string, RouteAnalysisResponse | null> | null

  // Room context (MUD integration)
  roomContext?: RoomContext | null
}

export default function Toolbar({
  sessions, selectedSession, onSessionChange, sessionDetails,
  axes, topRoutes, showAllRoutes, onTopRoutesChange, onShowAllRoutesChange,
  clustering, schema, selectedRange,
  filterState, onFilterStateChange, currentRouteData,
  roomContext,
}: ToolbarProps) {
  // When visitor, all controls are disabled
  const controlsDisabled = roomContext?.role === 'visitor'
  // When in micro_world room, session is locked
  const sessionLocked = roomContext?.roomType === 'micro_world'
  const {
    allAxes, colorAxisId, colorAxis2Id, shapeAxisId, gradient,
    outputAxes, outputColorAxisId, outputColorAxis2Id, outputGradient,
    outputColorAxis, outputColorAxis2,
    setColorAxisId, setColorAxis2Id, setShapeAxisId,
    setGradient, setOutputColorAxisId, setOutputColorAxis2Id, setOutputGradient,
  } = axes

  const { availableSchemas, selectedSchema, setSelectedSchema } = schema

  // Color preview
  const colorAxis = allAxes.find(a => a.id === colorAxisId)
  const colorAxis2 = allAxes.find(a => a.id === colorAxis2Id)
  const autoSecondaryGradient = GRADIENT_AUTO_PAIRS[gradient]
  const primaryValues = colorAxis?.values || (colorAxis ? [colorAxis.label_a, colorAxis.label_b] : [])
  const secondaryValues = colorAxis2?.values || (colorAxis2 ? [colorAxis2.label_a, colorAxis2.label_b] : undefined)
  const preview = primaryValues.length > 0
    ? getAxisPreview(primaryValues, gradient, secondaryValues)
    : []

  // Output color preview
  const outPrimaryValues = outputColorAxis?.values || (outputColorAxis ? [outputColorAxis.label_a, outputColorAxis.label_b] : [])
  const outSecondaryValues = outputColorAxis2?.values || (outputColorAxis2 ? [outputColorAxis2.label_a, outputColorAxis2.label_b] : undefined)
  const outPreview = outPrimaryValues.length > 0
    ? getAxisPreview(outPrimaryValues, outputGradient, outputColorAxis2Id !== 'none' ? outSecondaryValues : undefined)
    : []

  // Available labels for filter pills
  const availableLabels = useMemo(() => {
    if (!currentRouteData) return []
    const labels = new Set<string>()
    for (const data of Object.values(currentRouteData)) {
      if (data?.available_axes) {
        for (const axis of data.available_axes) {
          if (axis.id === 'label') {
            if (axis.values) {
              axis.values.forEach(v => labels.add(v))
            } else {
              labels.add(axis.label_a)
              labels.add(axis.label_b)
            }
          }
        }
      }
    }
    return Array.from(labels)
  }, [currentRouteData])

  const handleLabelToggle = (label: string) => {
    const newLabels = new Set(filterState.labels)
    if (newLabels.has(label)) {
      newLabels.delete(label)
    } else {
      newLabels.add(label)
    }
    onFilterStateChange({ ...filterState, labels: newLabels })
  }

  const completedSessions = sessions.filter(s => s.state === 'completed')

  return (
    <div className={`bg-white border-b border-gray-200 px-3 py-2 flex items-center gap-3 flex-wrap ${controlsDisabled ? 'opacity-60 pointer-events-none' : ''}`}>
      {/* Role badge */}
      {roomContext?.role === 'visitor' && (
        <span className="text-[10px] font-medium bg-amber-100 text-amber-800 border border-amber-300 rounded px-1.5 py-0.5">
          Visitor
        </span>
      )}
      {roomContext?.role === 'researcher' && (
        <span className="text-[10px] font-medium bg-green-100 text-green-800 border border-green-300 rounded px-1.5 py-0.5">
          Researcher
        </span>
      )}

      {/* Session selector */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-gray-500 font-medium">Session:</span>
        <select
          value={selectedSession}
          onChange={(e) => onSessionChange(e.target.value)}
          disabled={controlsDisabled || sessionLocked}
          className="px-1.5 py-0.5 text-xs border border-gray-300 rounded min-w-[140px]"
        >
          <option value="">Select session...</option>
          {completedSessions.map(s => (
            <option key={s.session_id} value={s.session_id}>{s.session_name}</option>
          ))}
        </select>
      </div>

      {selectedSession && (
        <>
          {/* Divider */}
          <div className="w-px h-6 bg-gray-300" />

          {/* Color axis + gradient */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-500 font-medium">Color:</span>
            <select
              value={colorAxisId}
              onChange={(e) => setColorAxisId(e.target.value)}
              className="px-1.5 py-0.5 text-xs border border-gray-300 rounded"
            >
              {allAxes.map(axis => (
                <option key={axis.id} value={axis.id}>{axis.label}</option>
              ))}
            </select>
            <select
              value={gradient}
              onChange={(e) => setGradient(e.target.value as GradientScheme)}
              className="px-1.5 py-0.5 text-xs border border-gray-300 rounded"
            >
              {Object.entries(GRADIENT_SCHEMES).map(([key, scheme]) => (
                <option key={key} value={key}>{scheme.name}</option>
              ))}
            </select>
          </div>

          {/* Blend axis */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-500 font-medium">Blend:</span>
            <select
              value={colorAxis2Id}
              onChange={(e) => setColorAxis2Id(e.target.value)}
              className="px-1.5 py-0.5 text-xs border border-gray-300 rounded"
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

          {/* Shape axis */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-500 font-medium">Shape:</span>
            <select
              value={shapeAxisId}
              onChange={(e) => setShapeAxisId(e.target.value)}
              className="px-1.5 py-0.5 text-xs border border-gray-300 rounded"
            >
              <option value="none">None</option>
              {allAxes.map(axis => (
                <option key={axis.id} value={axis.id}>{axis.label}</option>
              ))}
            </select>
          </div>

          {/* Color preview */}
          {preview.length > 0 && (
            <>
              <div className="w-px h-6 bg-gray-300" />
              <div className="flex items-center gap-1.5 flex-wrap">
                {preview.map(({ label, color }) => (
                  <div key={label} className="flex items-center gap-0.5" title={label}>
                    <div
                      className="rounded-sm border border-gray-300 flex-shrink-0"
                      style={{ backgroundColor: color, width: '10px', height: '10px' }}
                    />
                    <span className="text-[10px] text-gray-600">{label}</span>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Output colors (conditional) */}
          {outputAxes.length > 0 && (
            <>
              <div className="w-px h-6 bg-gray-300" />
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-gray-500 font-medium">Out:</span>
                <select
                  value={outputColorAxisId}
                  onChange={(e) => setOutputColorAxisId(e.target.value)}
                  className="px-1.5 py-0.5 text-xs border border-gray-300 rounded"
                >
                  <option value="">Match input</option>
                  {outputAxes.map(axis => (
                    <option key={axis.id} value={axis.id}>{axis.label}</option>
                  ))}
                </select>
                <select
                  value={outputGradient}
                  onChange={(e) => setOutputGradient(e.target.value as GradientScheme)}
                  className="px-1.5 py-0.5 text-xs border border-gray-300 rounded"
                >
                  {Object.entries(GRADIENT_SCHEMES).map(([key, scheme]) => (
                    <option key={key} value={key}>{scheme.name}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-gray-500 font-medium">Out Blend:</span>
                <select
                  value={outputColorAxis2Id}
                  onChange={(e) => setOutputColorAxis2Id(e.target.value)}
                  className="px-1.5 py-0.5 text-xs border border-gray-300 rounded"
                >
                  <option value="none">None</option>
                  {outputAxes.filter(a => a.id !== outputColorAxisId).map(axis => (
                    <option key={axis.id} value={axis.id}>{axis.label}</option>
                  ))}
                </select>
              </div>
              {/* Output color preview */}
              {outPreview.length > 0 && (
                <div className="flex items-center gap-1.5 flex-wrap">
                  {outPreview.map(({ label, color }) => (
                    <div key={label} className="flex items-center gap-0.5" title={label}>
                      <div
                        className="rounded-sm border border-gray-300 flex-shrink-0"
                        style={{ backgroundColor: color, width: '10px', height: '10px' }}
                      />
                      <span className="text-[10px] text-gray-600">{label}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* Divider */}
          <div className="w-px h-6 bg-gray-300" />

          {/* Expert route controls */}
          <div className="flex items-center gap-1.5">
            <label className="flex items-center gap-1 text-xs text-gray-700">
              <input
                type="checkbox"
                checked={showAllRoutes}
                onChange={(e) => onShowAllRoutesChange(e.target.checked)}
                className="w-3 h-3 rounded border-gray-300 text-blue-600"
              />
              All routes
            </label>
            {!showAllRoutes && (
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-gray-500">Top</span>
                <input
                  type="number"
                  value={topRoutes}
                  onChange={(e) => onTopRoutesChange(parseInt(e.target.value))}
                  min="5"
                  max="100"
                  className="w-12 px-1 py-0.5 text-xs border border-gray-300 rounded"
                />
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="w-px h-6 bg-gray-300" />

          {/* Schema + clustering */}
          <div className="flex items-center gap-1.5">
            {availableSchemas.length > 0 && (
              <>
                <span className="text-xs text-gray-500 font-medium">Schema:</span>
                <select
                  value={selectedSchema}
                  onChange={(e) => setSelectedSchema(e.target.value)}
                  className="px-1.5 py-0.5 text-xs border border-gray-300 rounded"
                >
                  <option value="">Compute fresh</option>
                  {availableSchemas.map(s => (
                    <option key={s.name} value={s.name}>{s.name}</option>
                  ))}
                </select>
              </>
            )}

            {/* Schema summary OR clustering params */}
            {selectedSchema ? (
              <span className="text-[10px] text-gray-500 font-mono bg-gray-50 rounded px-1.5 py-0.5">
                {(() => {
                  const s = availableSchemas.find(s => s.name === selectedSchema)
                  if (!s?.params) return selectedSchema
                  const p = s.params
                  const source = p.embedding_source === 'residual_stream' ? 'residual' : 'expert'
                  const method = (p.reduction_method || 'pca').toUpperCase()
                  const dims = p.reduction_dimensions || '?'
                  const cm = p.clustering_method || '?'
                  const counts = p.layer_cluster_counts || {}
                  const kValues = [...new Set(Object.values(counts) as number[])]
                  const kStr = kValues.length === 1 ? `K=${kValues[0]}` : kValues.map(v => `K=${v}`).join('/')
                  return `${source} · ${method} ${dims}D · ${cm} · ${kStr}`
                })()}
              </span>
            ) : (
              <div className="flex items-center gap-1.5 text-[10px]">
                <select value={clustering.embeddingSource} onChange={e => clustering.setEmbeddingSource(e.target.value)}
                  className="px-1 py-0.5 border border-gray-300 rounded text-[10px]">
                  <option value="expert_output">expert</option>
                  <option value="residual_stream">residual</option>
                </select>
                <select value={clustering.reductionMethod} onChange={e => clustering.setReductionMethod(e.target.value)}
                  className="px-1 py-0.5 border border-gray-300 rounded text-[10px]">
                  <option value="pca">PCA</option>
                  <option value="umap">UMAP</option>
                </select>
                <input type="number" value={clustering.reductionDims} onChange={e => clustering.setReductionDims(Number(e.target.value))}
                  min={2} max={256} className="w-8 px-0.5 py-0.5 border border-gray-300 rounded text-[10px]" />
                <span className="text-gray-400">D</span>
                <select value={clustering.clusteringMethod} onChange={e => clustering.setClusteringMethod(e.target.value)}
                  className="px-1 py-0.5 border border-gray-300 rounded text-[10px]">
                  <option value="hierarchical">hier</option>
                  <option value="kmeans">kmeans</option>
                </select>
                <span className="text-gray-400">K</span>
                <input type="number" value={clustering.globalClusterCount} onChange={e => clustering.setGlobalClusterCount(Number(e.target.value))}
                  min={2} max={16} className="w-8 px-0.5 py-0.5 border border-gray-300 rounded text-[10px]" />
              </div>
            )}
          </div>

          {/* Claude instruction (when schema selected) */}
          {selectedSchema && selectedSession && (() => {
            const currentRange = LAYER_RANGES[selectedRange as keyof typeof LAYER_RANGES]
            if (!currentRange) return null
            const lastWindow = currentRange.windows[currentRange.windows.length - 1]
            const windowStr = lastWindow ? `${lastWindow.layers[0]}-${lastWindow.layers[lastWindow.layers.length - 1]}` : '22-23'
            const instruction = `/analyze ${selectedSession} schema ${selectedSchema} window ${windowStr}`
            return (
              <>
                <div className="w-px h-6 bg-gray-300" />
                <div
                  className="text-[10px] font-mono bg-blue-50 border border-blue-200 rounded px-1.5 py-0.5 cursor-pointer hover:bg-blue-100"
                  title="Click to copy"
                  onClick={e => {
                    const el = e.currentTarget
                    navigator.clipboard?.writeText(el.textContent || '')
                  }}
                >
                  {instruction}
                </div>
              </>
            )
          })()}

          {/* Label filter pills */}
          {availableLabels.length > 0 && (
            <>
              <div className="w-px h-6 bg-gray-300" />
              <div className="flex items-center gap-1 flex-wrap">
                <span className="text-xs text-gray-500 font-medium">Labels:</span>
                {availableLabels.map(label => (
                  <button
                    key={label}
                    onClick={() => handleLabelToggle(label)}
                    className={`px-1.5 py-0.5 rounded text-[10px] border transition-colors ${
                      filterState.labels.size === 0 || filterState.labels.has(label)
                        ? 'bg-blue-100 border-blue-300 text-blue-800'
                        : 'bg-gray-100 border-gray-300 text-gray-500'
                    }`}
                  >
                    {label}
                  </button>
                ))}
                {filterState.labels.size > 0 && (
                  <button
                    onClick={() => onFilterStateChange({ ...filterState, labels: new Set() })}
                    className="text-[10px] text-gray-500 hover:text-gray-700"
                  >
                    clear
                  </button>
                )}
              </div>
            </>
          )}

          {/* Session info */}
          {sessionDetails && (
            <>
              <div className="w-px h-6 bg-gray-300" />
              <span className="text-[10px] text-gray-400">
                {sessionDetails.manifest?.probe_count} probes
                {sessionDetails.target_word && ` · "${sessionDetails.target_word}"`}
              </span>
            </>
          )}
        </>
      )}
    </div>
  )
}
