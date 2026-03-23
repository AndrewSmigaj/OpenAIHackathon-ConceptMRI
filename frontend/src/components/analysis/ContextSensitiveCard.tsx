import { getNodeColor, type GradientScheme } from '../../utils/colorBlending'
import SentenceHighlight from '../SentenceHighlight'
import ReactMarkdown from 'react-markdown'

export interface ContextSensitiveCardProps {
  cardType: 'expert' | 'highway' | 'cluster' | 'route'
  selectedData: any
  colorLabelA: string
  colorLabelB: string
  gradient: GradientScheme
  elementDescription?: string
  clusterAssignments?: Record<string, number>
  onClose?: () => void
}

export default function ContextSensitiveCard({ cardType, selectedData, colorLabelA, colorLabelB, gradient, elementDescription, clusterAssignments, onClose }: ContextSensitiveCardProps) {
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
  const isOutputNode = selectedData.name?.startsWith('Out:') || selectedData.id?.startsWith('Out:')

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

          {/* Label Distribution bars */}
          {labelStats.length > 0 && (
            <div>
              <p className="text-[10px] font-medium text-gray-500 mb-0.5">Label Distribution</p>
              <div className="space-y-0.5">
                {labelStats.map(stat => (
                  <div key={stat.category}>
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-gray-700 capitalize truncate">{stat.category}</span>
                      <span className="text-gray-500 flex-shrink-0 ml-1">{stat.count} ({stat.percentage.toFixed(0)}%)</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1">
                      <div className="bg-blue-500 h-1 rounded-full" style={{ width: `${Math.min(stat.percentage, 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Per-axis category distributions */}
          {axisDistributions && Object.keys(axisDistributions).length > 0 && (
            <div>
              <p className="text-[10px] font-medium text-gray-500 mb-0.5">Categories</p>
              <div className="space-y-1">
                {Object.entries(axisDistributions).map(([axisId, dist]) => {
                  const total = Object.values(dist).reduce((s, v) => s + v, 0)
                  return (
                    <div key={axisId}>
                      <p className="text-[10px] font-medium text-gray-600 capitalize">{axisId}</p>
                      {Object.entries(dist)
                        .sort(([, a], [, b]) => b - a)
                        .map(([value, count]) => {
                          const pct = total > 0 ? (count / total) * 100 : 0
                          return (
                            <div key={value} className="mb-0.5">
                              <div className="flex justify-between items-center text-[10px]">
                                <span className="text-gray-700 capitalize truncate">{value}</span>
                                <span className="text-gray-500 flex-shrink-0 ml-1">{count} ({pct.toFixed(0)}%)</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-1">
                                <div className="bg-indigo-400 h-1 rounded-full" style={{ width: `${Math.min(pct, 100)}%` }} />
                              </div>
                            </div>
                          )
                        })}
                    </div>
                  )
                })}
              </div>
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
          {elementDescription && (
            <div className="border-t border-gray-100 pt-1">
              <div className="prose prose-sm max-w-none text-[10px] text-gray-700">
                <ReactMarkdown>{elementDescription}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* Examples */}
          <div className="border-t border-gray-100 pt-1">
            <p className="text-[10px] font-medium text-gray-500 mb-0.5">
              Examples {examples.length > 0 && `(${rawExamples.length}${isOutputNode ? ', shuffled' : ''})`}
            </p>
            {Array.isArray(examples) && examples.length > 0 ? (
              isOutputNode ? (
                <div className="space-y-0.5 max-h-[500px] overflow-y-auto">
                  {examples.map((token: any, index: number) => {
                    const tokenColor = token.label && colorLabelA && colorLabelB
                      ? getNodeColor({ [token.label]: 1 }, colorLabelA, colorLabelB, undefined, undefined, gradient)
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
                    const tokenColor = token.label && colorLabelA && colorLabelB
                      ? getNodeColor({ [token.label]: 1 }, colorLabelA, colorLabelB, undefined, undefined, gradient)
                      : '#666666'
                    return (
                      <div key={token.probe_id || index} className="bg-gray-50 px-1.5 py-0.5 rounded">
                        <p className="text-[10px] text-gray-700 leading-snug">
                          {token.label && (
                            <span className="inline-block px-1 py-px text-[9px] font-medium rounded text-white capitalize mr-0.5 align-middle" style={{ backgroundColor: tokenColor }}>
                              {token.label}
                            </span>
                          )}
                          {token.input_text ? (
                            <SentenceHighlight text={token.input_text} targetWord={token.target_word || ''} color={tokenColor} />
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
