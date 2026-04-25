import type { SessionListItem, SessionDetailResponse } from '../../types/api'
import type { GradientScheme } from '../../utils/colorBlending'
import { getAxisPreview, GRADIENT_SCHEMES, GRADIENT_AUTO_PAIRS } from '../../utils/colorBlending'
import { LAYER_RANGES } from '../../constants/layerRanges'
import type { AxisControlsState } from '../../hooks/useAxisControls'
import type { SchemaManagementState } from '../../hooks/useSchemaManagement'
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

  // Schema (from useSchemaManagement)
  schema: SchemaManagementState
  selectedRange: string

  // Trajectory display
  maxTrajectories: number
  onMaxTrajectoriesChange: (n: number) => void

  // Ambiguity blend (binary secondary axis only)
  ambiguityBlendEnabled: boolean
  onAmbiguityBlendToggle: (enabled: boolean) => void
  ambiguousValue: string
  onAmbiguousValueChange: (val: string) => void

  // Room context (MUD integration)
  roomContext?: RoomContext | null

  // Unified run
  onRunAll: () => void
  canRunAll: boolean
}

export default function Toolbar({
  sessions, selectedSession, onSessionChange, sessionDetails,
  axes, topRoutes, showAllRoutes, onTopRoutesChange, onShowAllRoutesChange,
  schema, selectedRange,
  maxTrajectories, onMaxTrajectoriesChange,
  ambiguityBlendEnabled, onAmbiguityBlendToggle,
  ambiguousValue, onAmbiguousValueChange,
  roomContext,
  onRunAll, canRunAll,
}: ToolbarProps) {
  const controlsDisabled = roomContext?.role === 'visitor'
  const sessionLocked = roomContext?.roomType === 'micro_world'
  const {
    allAxes, colorAxisId, colorAxis2Id, shapeAxisId, gradient,
    outputAxes, outputColorAxisId, outputColorAxis2Id, outputGradient,
    outputColorAxis, outputColorAxis2,
    setColorAxisId, setColorAxis2Id, setShapeAxisId,
    setGradient, setOutputColorAxisId, setOutputColorAxis2Id, setOutputGradient,
  } = axes

  const { availableSchemas, selectedSchema, setSelectedSchema } = schema

  const colorAxis = allAxes.find(a => a.id === colorAxisId)
  const colorAxis2 = allAxes.find(a => a.id === colorAxis2Id)
  const autoSecondaryGradient = GRADIENT_AUTO_PAIRS[gradient]
  const primaryValues = colorAxis?.values || (colorAxis ? [colorAxis.label_a, colorAxis.label_b] : [])
  const secondaryValues = colorAxis2?.values || (colorAxis2 ? [colorAxis2.label_a, colorAxis2.label_b] : undefined)
  const preview = primaryValues.length > 0
    ? getAxisPreview(primaryValues, gradient, secondaryValues)
    : []

  const outPrimaryValues = outputColorAxis?.values || (outputColorAxis ? [outputColorAxis.label_a, outputColorAxis.label_b] : [])
  const outSecondaryValues = outputColorAxis2?.values || (outputColorAxis2 ? [outputColorAxis2.label_a, outputColorAxis2.label_b] : undefined)
  const outPreview = outPrimaryValues.length > 0
    ? getAxisPreview(outPrimaryValues, outputGradient, outputColorAxis2Id !== 'none' ? outSecondaryValues : undefined)
    : []

  const completedSessions = sessions.filter(s => s.state === 'completed')

  const noSession = !selectedSession
  const noSchema = !selectedSchema
  const ctrl = "px-2 py-1 text-xs border border-gray-300 rounded bg-white disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
  const row = "flex items-center gap-3"
  const label = "text-xs text-gray-700 font-medium w-[90px] text-right flex-shrink-0"
  const panelTitle = "text-xs font-semibold text-gray-800 uppercase tracking-wide border-b border-gray-300 pb-1.5 mb-2"

  const selectedSchemaMeta = availableSchemas.find(s => s.name === selectedSchema)
  const sampleSize = selectedSchemaMeta?.sample_size ?? 0
  const showAmbiguityBlend = !!secondaryValues && secondaryValues.length === 2

  return (
    <div className={`bg-gray-50 border-b border-gray-300 px-3 py-2 space-y-2 ${controlsDisabled ? 'opacity-60 pointer-events-none' : ''}`}>
      {/* Session bar */}
      <div className="flex items-center gap-3">
        {roomContext?.role === 'visitor' && (
          <span className="text-[10px] font-medium bg-amber-100 text-amber-800 border border-amber-300 rounded px-1.5 py-0.5">Visitor</span>
        )}
        {roomContext?.role === 'researcher' && (
          <span className="text-[10px] font-medium bg-green-100 text-green-800 border border-green-300 rounded px-1.5 py-0.5">Researcher</span>
        )}

        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-600 font-medium">Session</span>
          <select
            value={selectedSession}
            onChange={(e) => onSessionChange(e.target.value)}
            disabled={controlsDisabled || sessionLocked}
            className={`${ctrl} min-w-[180px]`}
          >
            <option value="">Select session...</option>
            {completedSessions.map(s => (
              <option key={s.session_id} value={s.session_id}>{s.session_name}</option>
            ))}
          </select>
        </div>

        {sessionDetails && (
          <span className="text-xs text-gray-400">
            {sessionDetails.manifest?.probe_count} probes
            {sessionDetails.target_word && ` · "${sessionDetails.target_word}"`}
          </span>
        )}

        <div className="flex-1" />

        <button
          onClick={onRunAll}
          disabled={noSession || noSchema || !canRunAll}
          className="px-4 py-1 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          Run
        </button>
      </div>

      {/* Two-panel layout */}
      <div className={`grid grid-cols-2 gap-3 ${noSession ? 'opacity-40 pointer-events-none' : ''}`}>

        {/* LEFT PANEL: Analysis & Routes */}
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          <div className={panelTitle}>Analysis</div>
          <div className="space-y-2">
            {/* Schema */}
            <div className={row}>
              <span className={label}>Schema</span>
              <select value={selectedSchema} onChange={(e) => setSelectedSchema(e.target.value)}
                disabled={noSession} className={`${ctrl} flex-1`}>
                <option value="">Select schema…</option>
                {availableSchemas.map(s => (
                  <option key={s.name} value={s.name}>{s.name}</option>
                ))}
              </select>
            </div>

            {/* Schema info readout */}
            {selectedSchemaMeta && (
              <div className={row}>
                <span className={label} />
                <span className="text-xs text-gray-500 font-mono bg-gray-50 rounded px-2 py-0.5 border border-gray-200">
                  {(() => {
                    const p = selectedSchemaMeta.params || {}
                    const source = p.embedding_source === 'residual_stream' ? 'residual' : 'expert'
                    const method = (p.reduction_method || 'pca').toUpperCase()
                    const dims = p.reduction_dimensions || '?'
                    const cm = p.clustering_method || '?'
                    const counts = p.layer_cluster_counts || {}
                    const kValues = [...new Set(Object.values(counts) as number[])]
                    const kStr = kValues.length === 1 ? `K=${kValues[0]}` : kValues.length > 0 ? kValues.map(v => `K=${v}`).join('/') : ''
                    const sample = selectedSchemaMeta.sample_size != null ? ` · n=${selectedSchemaMeta.sample_size}` : ''
                    return `${source} · ${method} ${dims}D · ${cm}${kStr ? ' · ' + kStr : ''}${sample}`
                  })()}
                </span>
              </div>
            )}

            {/* Trajectories — display-only slider */}
            {selectedSchemaMeta && sampleSize > 0 && (
              <div className={row}>
                <span className={label}>Trajectories</span>
                <input
                  type="range"
                  min={Math.min(10, sampleSize)}
                  max={sampleSize}
                  step={1}
                  value={Math.min(maxTrajectories, sampleSize)}
                  onChange={e => onMaxTrajectoriesChange(Number(e.target.value))}
                  className="flex-1 accent-blue-600"
                  title="Max trajectories to render in the 3D plot"
                />
                <span className="w-12 text-right tabular-nums text-xs text-gray-700">
                  {Math.min(maxTrajectories, sampleSize)} / {sampleSize}
                </span>
              </div>
            )}

            {/* Routes */}
            <div className={row}>
              <span className={label}>Routes</span>
              <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
                <input type="checkbox" checked={showAllRoutes}
                  onChange={(e) => onShowAllRoutesChange(e.target.checked)}
                  disabled={noSession} className="w-3 h-3 rounded" />
                Show all
              </label>
              <div className="border-l border-gray-300 h-4 ml-2" />
              <div className={`flex items-center gap-2 transition-opacity ${showAllRoutes ? 'opacity-40' : ''}`}>
                <span className="text-xs text-gray-500 font-medium">Top</span>
                <input type="number" value={topRoutes}
                  onChange={(e) => onTopRoutesChange(parseInt(e.target.value))}
                  disabled={noSession || showAllRoutes} min="5" max="100"
                  className={`${ctrl} w-16`} />
              </div>
            </div>

            {/* Claude instruction */}
            {selectedSchema && selectedSession && (() => {
              const currentRange = LAYER_RANGES[selectedRange as keyof typeof LAYER_RANGES]
              if (!currentRange) return null
              const lastWindow = currentRange.windows[currentRange.windows.length - 1]
              const windowStr = lastWindow ? `${lastWindow.layers[0]}-${lastWindow.layers[lastWindow.layers.length - 1]}` : '22-23'
              const instruction = `/analyze ${selectedSession} schema ${selectedSchema} window ${windowStr}`
              return (
                <div className={row}>
                  <span className={label} />
                  <div className="text-xs font-mono bg-blue-50 border border-blue-200 rounded px-2 py-0.5 cursor-pointer hover:bg-blue-100 transition-colors"
                    title="Click to copy"
                    onClick={e => { navigator.clipboard?.writeText(e.currentTarget.textContent || '') }}>
                    {instruction}
                  </div>
                </div>
              )
            })()}
          </div>
        </div>

        {/* RIGHT PANEL: Visual Encoding */}
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          <div className={panelTitle}>Visual Encoding</div>
          <div className="space-y-2">
            {/* Input section label */}
            <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">Input</div>

            {/* Color */}
            <div className={row}>
              <span className={label}>Color Axis</span>
              <select value={colorAxisId} onChange={(e) => setColorAxisId(e.target.value)}
                disabled={noSession} className={ctrl}>
                {allAxes.length === 0 && <option value="">No axes loaded</option>}
                {allAxes.map(axis => (
                  <option key={axis.id} value={axis.id}>{axis.label}</option>
                ))}
              </select>
              <select value={gradient} onChange={(e) => setGradient(e.target.value as GradientScheme)}
                disabled={noSession} className={ctrl}>
                {Object.entries(GRADIENT_SCHEMES).map(([key, scheme]) => (
                  <option key={key} value={key}>{scheme.name}</option>
                ))}
              </select>
            </div>

            {/* Blend */}
            <div className={row}>
              <span className={label}>Blend Axis</span>
              <select value={colorAxis2Id} onChange={(e) => setColorAxis2Id(e.target.value)}
                disabled={noSession} className={ctrl}>
                <option value="none">None</option>
                {allAxes.filter(a => a.id !== colorAxisId).map(axis => (
                  <option key={axis.id} value={axis.id}>{axis.label}</option>
                ))}
              </select>
              {colorAxis2Id !== 'none' && (
                <span className="text-xs text-gray-400">{GRADIENT_SCHEMES[autoSecondaryGradient]?.name}</span>
              )}
            </div>

            {/* Ambiguity blend (binary secondary axis only) */}
            {showAmbiguityBlend && (
              <div className={row}>
                <span className={label}>Ambig. blend</span>
                <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
                  <input type="checkbox" checked={ambiguityBlendEnabled}
                    onChange={(e) => onAmbiguityBlendToggle(e.target.checked)}
                    className="w-3 h-3 rounded" />
                  Enable
                </label>
                {ambiguityBlendEnabled && (
                  <>
                    <span className="text-xs text-gray-500">Pole</span>
                    <select value={ambiguousValue} onChange={(e) => onAmbiguousValueChange(e.target.value)}
                      className={ctrl}>
                      {secondaryValues!.map(v => (
                        <option key={v} value={v}>{v}</option>
                      ))}
                    </select>
                  </>
                )}
              </div>
            )}

            {/* Shape */}
            <div className={row}>
              <span className={label}>Shape Axis</span>
              <select value={shapeAxisId} onChange={(e) => setShapeAxisId(e.target.value)}
                disabled={noSession} className={ctrl}>
                <option value="none">None</option>
                {allAxes.map(axis => (
                  <option key={axis.id} value={axis.id}>{axis.label}</option>
                ))}
              </select>
            </div>

            {/* Color preview */}
            {preview.length > 0 && (
              <div className={row}>
                <span className={label} />
                <div className="flex items-center gap-2 flex-wrap">
                  {preview.map(({ label: lbl, color }) => (
                    <div key={lbl} className="flex items-center gap-1" title={lbl}>
                      <div className="w-3 h-3 rounded-sm border border-gray-300 flex-shrink-0"
                        style={{ backgroundColor: color }} />
                      <span className="text-xs text-gray-600">{lbl}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Output section — always visible, grayed when no output axes */}
            <div className="border-t border-gray-200 pt-2 mt-1" />
            <div className={`space-y-2 ${outputAxes.length === 0 ? 'opacity-40 pointer-events-none' : ''}`}>
              <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">Output</div>

              <div className={row}>
                <span className={label}>Color Axis</span>
                <select value={outputColorAxisId} onChange={(e) => setOutputColorAxisId(e.target.value)}
                  disabled={outputAxes.length === 0} className={ctrl}>
                  <option value="">Match input</option>
                  {outputAxes.map(axis => (
                    <option key={axis.id} value={axis.id}>{axis.label}</option>
                  ))}
                </select>
                <select value={outputGradient} onChange={(e) => setOutputGradient(e.target.value as GradientScheme)}
                  disabled={outputAxes.length === 0} className={ctrl}>
                  {Object.entries(GRADIENT_SCHEMES).map(([key, scheme]) => (
                    <option key={key} value={key}>{scheme.name}</option>
                  ))}
                </select>
              </div>

              <div className={row}>
                <span className={label}>Blend Axis</span>
                <select value={outputColorAxis2Id} onChange={(e) => setOutputColorAxis2Id(e.target.value)}
                  disabled={outputAxes.length === 0} className={ctrl}>
                  <option value="none">None</option>
                  {outputAxes.filter(a => a.id !== outputColorAxisId).map(axis => (
                    <option key={axis.id} value={axis.id}>{axis.label}</option>
                  ))}
                </select>
              </div>

              {outPreview.length > 0 && (
                <div className={row}>
                  <span className={label} />
                  <div className="flex items-center gap-2 flex-wrap">
                    {outPreview.map(({ label: lbl, color }) => (
                      <div key={lbl} className="flex items-center gap-1" title={lbl}>
                        <div className="w-3 h-3 rounded-sm border border-gray-300 flex-shrink-0"
                          style={{ backgroundColor: color }} />
                        <span className="text-xs text-gray-600">{lbl}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
