import { getNodeColor, getAxisColor, rgbToHex, type GradientScheme } from '../../utils/colorBlending'
import { isOutputNode as checkIsOutputNode } from '../../constants/outputNodes'
import SentenceHighlight from '../SentenceHighlight'
import ReactMarkdown from 'react-markdown'

export interface ContextSensitiveCardProps {
  cardType: 'expert' | 'highway' | 'cluster' | 'route'
  selectedData: any
  primaryValues: string[]
  gradient: GradientScheme
  elementDescription?: string
  clusterAssignments?: Record<string, number>
  onClose?: () => void
}

export default function ContextSensitiveCard({ cardType, selectedData, primaryValues, gradient, elementDescription, clusterAssignments, onClose }: ContextSensitiveCardProps) {
  const hasRichData = Boolean(selectedData?._fullData)
  const isRoute = cardType === 'route' || cardType === 'highway'

  // Extract distributions for ALL card types (not just experts)
  const labelDistribution = hasRichData && selectedData?.label_distribution
    ? selectedData.label_distribution as Record<string, number>
    : null

  const axisDistributions = hasRichData && selectedData?.category_distributions
    ? selectedData.category_distributions as Record<string, Record<string, number>>
    : null

  if (!selectedData) {
    return (
      <div className="bg-gray-50 rounded border-2 border-dashed border-gray-300 p-4 text-center">
        <p className="text-[10px] text-gray-400">Click a node or route for details</p>
      </div>
    )
  }

  const getCardTitle = () => {
    if (hasRichData) {
      switch (cardType) {
        case 'expert': return `Expert ${selectedData.name || selectedData.expertId || 'E?'}`
        case 'highway': return `Route ${selectedData.signature || '?→?'}`
        case 'cluster': return selectedData.name || `Cluster ${selectedData.clusterId || 'C?'}`
        case 'route': return `Route ${selectedData.signature || '?→?'}`
      }
    }
    switch (cardType) {
      case 'expert': return `Expert ${selectedData.expertId || 'E?'}`
      case 'highway': return `Highway Route`
      case 'cluster': return `Cluster ${selectedData.clusterId || 'C?'}`
      case 'route': return `Trajectory Route`
    }
  }

  // Compute label distribution stats (for bars, no chi-square)
  const labelStats = labelDistribution
    ? Object.entries(labelDistribution)
        .map(([category, count]) => {
          const total = Object.values(labelDistribution).reduce((s, v) => s + v, 0)
          return { category, count, percentage: total > 0 ? (count / total) * 100 : 0 }
        })
        .sort((a, b) => b.count - a.count)
    : []

  // Examples
  const rawExamples = selectedData.tokens || selectedData.example_tokens || []
  const isOutputNode = checkIsOutputNode(selectedData.name || '') || checkIsOutputNode(selectedData.id || '')

  const shuffled = (arr: any[]) => {
    const a = [...arr]
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]]
    }
    return a
  }

  const examples = isOutputNode ? shuffled(rawExamples) : rawExamples.slice(0, 20)

  return (
    <div className="bg-white rounded border border-gray-200 p-2 flex flex-col overflow-hidden" style={{ overflowWrap: 'break-word', wordBreak: 'break-word' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-1.5 min-w-0">
        <h3 className="text-xs font-semibold text-gray-900 truncate flex-1 min-w-0">
          {getCardTitle()}
          {hasRichData && typeof selectedData.layer === 'number' && (
            <span className="text-[10px] text-gray-500 font-normal ml-1">L{selectedData.layer}</span>
          )}
        </h3>
        {onClose && (
          <button onClick={onClose} className="flex-shrink-0 ml-1 text-gray-400 hover:text-gray-600 text-sm leading-none">&times;</button>
        )}
      </div>

      {hasRichData ? (
        <div className="flex-1 overflow-y-auto space-y-1.5" style={{ overflowWrap: 'break-word', wordBreak: 'break-word' }}>
          {/* Quick metrics */}
          <div className="flex gap-1.5 text-[10px]">
            <div className="bg-gray-50 px-1.5 py-0.5 rounded flex-1">
              <span className="text-gray-500">Tokens </span>
              <span className="font-semibold text-gray-900">{selectedData.token_count ?? 0}</span>
            </div>
            <div className="bg-gray-50 px-1.5 py-0.5 rounded flex-1">
              <span className="text-gray-500">Cov </span>
              <span className="font-semibold text-gray-900">{selectedData.coverage ?? 0}%</span>
            </div>
          </div>

          {isRoute && (
            <div className="flex gap-1.5 text-[10px]">
              <div className="bg-gray-50 px-1.5 py-0.5 rounded flex-1">
                <span className="text-gray-500">Flow </span>
                <span className="font-semibold text-gray-900">{selectedData.value || selectedData.count || 0}</span>
              </div>
              {typeof selectedData.avg_confidence === 'number' && (
                <div className="bg-gray-50 px-1.5 py-0.5 rounded flex-1">
                  <span className="text-gray-500">Conf </span>
                  <span className="font-semibold text-gray-900">{(selectedData.avg_confidence * 100).toFixed(0)}%</span>
                </div>
              )}
            </div>
          )}

          {/* Specialization */}
          {selectedData.specialization && (
            <p className="text-[10px] text-gray-600 italic">{selectedData.specialization}</p>
          )}

          {/* Label Distribution — stacked bar */}
          {labelStats.length > 0 && (
            <div>
              <p className="text-[10px] font-medium text-gray-500 mb-0.5">Input Labels</p>
              <div className="flex rounded overflow-hidden border border-gray-200" style={{ height: 20 }}>
                {labelStats.map(stat => {
                  const color = primaryValues.length > 0
                    ? rgbToHex(getAxisColor(stat.category, primaryValues, gradient))
                    : '#6366f1'
                  return (
                    <div
                      key={stat.category}
                      className="flex items-center justify-center overflow-hidden"
                      style={{ width: `${stat.percentage}%`, backgroundColor: color, minWidth: stat.percentage > 0 ? 4 : 0 }}
                      title={`${stat.category}: ${stat.count} (${stat.percentage.toFixed(0)}%)`}
                    >
                      {stat.percentage >= 15 && (
                        <span className="text-[8px] font-medium text-white truncate px-0.5" style={{ textShadow: '0 0 2px rgba(0,0,0,0.5)' }}>
                          {stat.category.slice(0, 6)} {stat.percentage.toFixed(0)}%
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
              <div className="flex flex-wrap gap-x-2 gap-y-0 mt-0.5">
                {labelStats.map(stat => {
                  const color = primaryValues.length > 0
                    ? rgbToHex(getAxisColor(stat.category, primaryValues, gradient))
                    : '#6366f1'
                  return (
                    <span key={stat.category} className="inline-flex items-center gap-0.5 text-[9px] text-gray-600">
                      <span className="inline-block w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: color }} />
                      <span className="capitalize">{stat.category}</span>
                      <span className="text-gray-400">{stat.percentage.toFixed(0)}%</span>
                    </span>
                  )
                })}
              </div>
            </div>
          )}

          {/* Per-axis category distributions — stacked bars */}
          {axisDistributions && Object.keys(axisDistributions).length > 0 && (
            <div className="space-y-1">
              {Object.entries(axisDistributions).map(([axisId, dist]) => {
                const total = Object.values(dist).reduce((s, v) => s + v, 0)
                if (total === 0) return null
                const sorted = Object.entries(dist).sort(([, a], [, b]) => b - a)
                const axisValues = sorted.map(([v]) => v)
                return (
                  <div key={axisId}>
                    <p className="text-[10px] font-medium text-gray-500 mb-0.5 capitalize">{axisId}</p>
                    <div className="flex rounded overflow-hidden border border-gray-200" style={{ height: 20 }}>
                      {sorted.map(([value, count]) => {
                        const pct = (count / total) * 100
                        const color = axisValues.length > 0
                          ? rgbToHex(getAxisColor(value, axisValues, gradient))
                          : '#6366f1'
                        return (
                          <div
                            key={value}
                            className="flex items-center justify-center overflow-hidden"
                            style={{ width: `${pct}%`, backgroundColor: color, minWidth: pct > 0 ? 4 : 0 }}
                            title={`${value}: ${count} (${pct.toFixed(0)}%)`}
                          >
                            {pct >= 15 && (
                              <span className="text-[8px] font-medium text-white truncate px-0.5" style={{ textShadow: '0 0 2px rgba(0,0,0,0.5)' }}>
                                {value.slice(0, 6)} {pct.toFixed(0)}%
                              </span>
                            )}
                          </div>
                        )
                      })}
                    </div>
                    <div className="flex flex-wrap gap-x-2 gap-y-0 mt-0.5">
                      {sorted.map(([value, count]) => {
                        const pct = (count / total) * 100
                        const color = axisValues.length > 0
                          ? rgbToHex(getAxisColor(value, axisValues, gradient))
                          : '#6366f1'
                        return (
                          <span key={value} className="inline-flex items-center gap-0.5 text-[9px] text-gray-600">
                            <span className="inline-block w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: color }} />
                            <span className="capitalize">{value}</span>
                            <span className="text-gray-400">{pct.toFixed(0)}%</span>
                          </span>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Cluster path */}
          {cardType === 'route' && clusterAssignments && Object.keys(clusterAssignments).length > 0 && (
            <div>
              <p className="text-[10px] font-medium text-gray-500 mb-0.5">Cluster Path</p>
              <div className="flex flex-wrap gap-0.5">
                {Object.entries(clusterAssignments)
                  .sort(([a], [b]) => Number(a) - Number(b))
                  .map(([layer, clusterId]) => (
                    <span key={layer} className="px-1 py-px bg-blue-50 text-blue-700 rounded text-[9px]">
                      L{layer}→C{clusterId}
                    </span>
                  ))}
              </div>
            </div>
          )}

          {/* AI description */}
          {elementDescription ? (
            <div className="border-t border-gray-100 pt-1">
              <div className="prose prose-sm max-w-none text-[10px] text-gray-700">
                <ReactMarkdown>{elementDescription}</ReactMarkdown>
              </div>
            </div>
          ) : (cardType === 'cluster' || cardType === 'expert') ? (
            <p className="text-[9px] text-gray-400 italic border-t border-gray-100 pt-1">
              No AI description. Run /analyze with a saved schema to generate cluster labels.
            </p>
          ) : null}

          {/* Examples */}
          <div className="border-t border-gray-100 pt-1">
            <p className="text-[10px] font-medium text-gray-500 mb-0.5">
              Examples {examples.length > 0 && `(${rawExamples.length}${isOutputNode ? ', shuffled' : ''})`}
            </p>
            {Array.isArray(examples) && examples.length > 0 ? (
              isOutputNode ? (
                <div className="space-y-0.5 max-h-[500px] overflow-y-auto">
                  {examples.map((token: any, index: number) => {
                    const tokenColor = token.label && primaryValues.length > 0
                      ? getNodeColor({ [token.label]: 1 }, primaryValues, gradient)
                      : '#666666'
                    return (
                      <div key={token.probe_id || index} className="bg-gray-50 px-1.5 py-0.5 rounded">
                        <div className="flex items-start gap-0.5 flex-wrap">
                          {token.label && (
                            <span className="inline-block px-1 py-px text-[9px] font-medium rounded text-white capitalize" style={{ backgroundColor: tokenColor }}>
                              {token.label}
                            </span>
                          )}
                          {token.output_category && (
                            <span className="inline-block px-1 py-px text-[9px] font-medium rounded bg-purple-100 text-purple-700">
                              {token.output_category}
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-gray-600 leading-snug mt-0.5">
                          {token.generated_text || <span className="italic text-gray-400">no output</span>}
                        </p>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="space-y-0.5 max-h-[400px] overflow-y-auto">
                  {examples.map((token: any, index: number) => {
                    const tokenColor = token.label && primaryValues.length > 0
                      ? getNodeColor({ [token.label]: 1 }, primaryValues, gradient)
                      : '#666666'

                    // Use backend's target_char_offset when available (same as Q4 panel).
                    // Falls back to lastIndexOf for legacy data without offsets.
                    const inputTextOffset = token.target_char_offset != null
                      ? token.target_char_offset
                      : token.input_text?.toLowerCase().lastIndexOf((token.target_word || '').toLowerCase()) ?? -1

                    // For game_text: target_char_offset is relative to input_text,
                    // so derive the position within game_text.
                    let gameTextOffset = token.game_text?.toLowerCase().lastIndexOf((token.target_word || '').toLowerCase()) ?? -1
                    if (token.target_char_offset != null && token.input_text && token.game_text) {
                      const gtStart = token.input_text.indexOf(token.game_text)
                      if (gtStart >= 0) {
                        const rel = token.target_char_offset - gtStart
                        if (rel >= 0 && rel < token.game_text.length) {
                          gameTextOffset = rel
                        }
                      }
                    }

                    // Agent session: rich card with INPUT / ANALYSIS / OUTPUT sections.
                    // Gate on actual tick-log payload (truthy strings), not the
                    // presence of the key — post-backend-enrichment every token
                    // dict has these keys (possibly null) for sentence captures.
                    if (token.game_text || token.analysis || token.action) {
                      return (
                        <div key={token.probe_id || index} className="bg-gray-50 px-1.5 py-1 rounded space-y-1">
                          <div className="flex items-center gap-1">
                            {token.label && (
                              <span className="inline-block px-1 py-px text-[9px] font-medium rounded text-white capitalize" style={{ backgroundColor: tokenColor }}>
                                {token.label}
                              </span>
                            )}
                            {token.step !== undefined && token.step !== null && (
                              <span className="text-[9px] text-gray-400">Step {token.step}</span>
                            )}
                            {token.output_category && (
                              <span className="px-1 py-px text-[9px] font-medium rounded bg-purple-100 text-purple-700">
                                {token.output_category}
                              </span>
                            )}
                          </div>

                          {/* SYSTEM PROMPT — collapsed by default; identical across probes in a session */}
                          {token.system_prompt && (
                            <details className="text-[9px] text-gray-500">
                              <summary className="cursor-pointer uppercase tracking-wide font-semibold">System prompt</summary>
                              <div className="mt-0.5 bg-gray-50 rounded px-1.5 py-1 whitespace-pre-wrap text-gray-600 leading-snug">
                                {token.system_prompt}
                              </div>
                            </details>
                          )}

                          {/* GAME INPUT — this turn's MUD state */}
                          <div>
                            <div className="text-[9px] font-semibold uppercase tracking-wide text-gray-500 mb-0.5">Game input</div>
                            <div className="text-[10px] text-gray-700 leading-snug bg-gray-100 rounded px-1.5 py-1 whitespace-pre-wrap">
                              {token.game_text ? (
                                <SentenceHighlight text={token.game_text} targetWord={token.target_word || ''} color={tokenColor} charOffset={gameTextOffset} />
                              ) : token.input_text ? (
                                <SentenceHighlight text={token.input_text} targetWord={token.target_word || ''} color={tokenColor} charOffset={inputTextOffset} />
                              ) : (
                                <span className="italic text-gray-400">(no input text)</span>
                              )}
                            </div>
                          </div>

                          {/* FULL PROMPT — collapsed; only rendered when input_text differs
                              from game_text (turn_id > 0 with accumulated prior turns). */}
                          {token.input_text && token.input_text !== token.game_text && (
                            <details className="text-[9px] text-gray-400">
                              <summary className="cursor-pointer">Full prompt (all turns)</summary>
                              <div className="mt-0.5 text-gray-600 whitespace-pre-wrap bg-gray-50 rounded px-1.5 py-1">
                                {token.input_text}
                              </div>
                            </details>
                          )}

                          {/* ANALYSIS — model's internal reasoning */}
                          {token.analysis && (
                            <div>
                              <div className="text-[9px] font-semibold uppercase tracking-wide text-gray-500 mb-0.5">Analysis</div>
                              <div className="bg-teal-50 rounded px-1.5 py-1">
                                <p className="text-[9px] text-teal-800 leading-snug">{token.analysis}</p>
                              </div>
                            </div>
                          )}

                          {/* OUTPUT — action taken + raw generated text */}
                          {(token.action || token.generated_text) && (
                            <div>
                              <div className="text-[9px] font-semibold uppercase tracking-wide text-gray-500 mb-0.5">Output</div>
                              {token.action && (
                                <p className="text-[10px] font-bold text-amber-600 leading-snug">
                                  {'>'} {token.action}
                                </p>
                              )}
                              {token.generated_text && (
                                <p className="text-[9px] text-gray-600 mt-0.5 leading-snug italic">{token.generated_text}</p>
                              )}
                            </div>
                          )}

                        </div>
                      )
                    }

                    // Standard card (sentence sets, temporal)
                    return (
                      <div key={token.probe_id || index} className="bg-gray-50 px-1.5 py-0.5 rounded">
                        <p className="text-[10px] text-gray-700 leading-snug">
                          {token.label && (
                            <span className="inline-block px-1 py-px text-[9px] font-medium rounded text-white capitalize mr-0.5 align-middle" style={{ backgroundColor: tokenColor }}>
                              {token.label}
                            </span>
                          )}
                          {token.input_text ? (
                            <SentenceHighlight text={token.input_text} targetWord={token.target_word || ''} color={tokenColor} charOffset={inputTextOffset} />
                          ) : (
                            <span className="text-gray-500">"{token.target_word || 'N/A'}"</span>
                          )}
                        </p>
                        {token.generated_text && (
                          <p className="text-[9px] text-blue-600 mt-0.5 leading-snug italic">→ {token.generated_text}</p>
                        )}
                        {token.output_category && (
                          <span className="inline-block mt-0.5 px-1 py-px text-[9px] font-medium rounded bg-purple-100 text-purple-700">
                            {token.output_category}
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>
              )
            ) : (
              <p className="text-[10px] text-gray-400 italic">No examples available</p>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-2 text-[10px]">
          <div className="flex justify-between">
            <span className="text-gray-500">Population</span>
            <span className="font-medium text-gray-900">{selectedData.population || '?'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Coverage</span>
            <span className="font-medium text-gray-900">{selectedData.coverage || '0'}%</span>
          </div>
          {selectedData.specialization && (
            <p className="text-[10px] text-gray-600 border-t border-gray-100 pt-1">{selectedData.specialization}</p>
          )}
        </div>
      )}
    </div>
  )
}
