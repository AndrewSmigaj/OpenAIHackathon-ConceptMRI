import { useState, useEffect } from 'react'
import { ChartBarIcon, SparklesIcon } from '../icons/Icons'
import { getNodeColor, type GradientScheme } from '../../utils/colorBlending'
import SentenceHighlight from '../SentenceHighlight'
import ReactMarkdown from 'react-markdown'

// @ts-ignore
import jStat from 'jStat'

interface StatisticalAnalysis {
  totalTokens: number
  categoryStats: Array<{
    category: string
    count: number
    percentage: number
  }>
  entropy: number
  normalizedEntropy: number
  diversity: string
  dominantCategory: string
  concentrationRatio: number
  testStatistic: number
  pValue: number
  isSignificant: boolean
  testType: string
}

function calculateStatisticalAnalysis(distribution: Record<string, number>, allLabels?: string[]): StatisticalAnalysis {
  // Ensure all known labels are represented (missing = 0 count)
  const fullDistribution = { ...distribution }
  if (allLabels) {
    for (const label of allLabels) {
      if (!(label in fullDistribution)) fullDistribution[label] = 0
    }
  }
  const categories = Object.keys(fullDistribution)
  const counts = Object.values(fullDistribution)
  const totalTokens = counts.reduce((sum, count) => sum + count, 0)

  if (categories.length === 0 || totalTokens === 0) {
    return {
      totalTokens: 0,
      categoryStats: [],
      entropy: 0,
      normalizedEntropy: 0,
      diversity: 'No data',
      dominantCategory: 'None',
      concentrationRatio: 0,
      testStatistic: 0,
      pValue: 1,
      isSignificant: false,
      testType: 'None'
    }
  }

  // Calculate category statistics
  const categoryStats = categories.map((category, index) => {
    const count = counts[index]
    return {
      category,
      count,
      percentage: (count / totalTokens) * 100,
      probability: count / totalTokens
    }
  }).sort((a, b) => b.count - a.count)

  // Calculate Shannon entropy: H = -Σ(p * log2(p))
  let entropy = 0
  categoryStats.forEach(stat => {
    if (stat.probability > 0) {
      entropy -= stat.probability * Math.log2(stat.probability)
    }
  })

  // Normalize entropy (0 = completely concentrated, 1 = perfectly uniform)
  const maxEntropy = Math.log2(categories.length)
  const normalizedEntropy = maxEntropy > 0 ? entropy / maxEntropy : 0

  // Classify diversity based on normalized entropy
  let diversity: string
  if (normalizedEntropy < 0.3) {
    diversity = 'Highly concentrated'
  } else if (normalizedEntropy < 0.6) {
    diversity = 'Moderately concentrated'
  } else if (normalizedEntropy < 0.85) {
    diversity = 'Well distributed'
  } else {
    diversity = 'Uniformly distributed'
  }

  const dominantCategory = categoryStats[0].category
  const concentrationRatio = categoryStats[0].percentage

  // Chi-square test against uniform distribution across all categories
  // With only 1 category, degrees of freedom = 0 — test is undefined
  let testStatistic = 0
  let pValue = 1
  let isSignificant = false
  const testType = categories.length > 1 ? 'Chi-square test vs uniform distribution' : 'N/A (single category)'

  if (categories.length > 1) {
    const expectedPerCategory = totalTokens / categories.length
    categoryStats.forEach(stat => {
      testStatistic += Math.pow(stat.count - expectedPerCategory, 2) / expectedPerCategory
    })
    const degreesOfFreedom = categories.length - 1
    pValue = 1 - jStat.chisquare.cdf(testStatistic, degreesOfFreedom)
    isSignificant = pValue < 0.05
  }

  return {
    totalTokens,
    categoryStats: categoryStats.map(({ probability, ...rest }) => rest), // Remove probability from output
    entropy,
    normalizedEntropy,
    diversity,
    dominantCategory,
    concentrationRatio,
    testStatistic,
    pValue,
    isSignificant,
    testType
  }
}

export interface ContextSensitiveCardProps {
  cardType: 'expert' | 'highway' | 'cluster' | 'route'
  selectedData: any
  colorLabelA: string
  colorLabelB: string
  gradient: GradientScheme
  elementDescription?: string
  clusterAssignments?: Record<string, number>
}

export default function ContextSensitiveCard({ cardType, selectedData, colorLabelA, colorLabelB, gradient, elementDescription, clusterAssignments }: ContextSensitiveCardProps) {
  const [activeTab, setActiveTab] = useState<'details' | 'examples' | 'ai'>('details')

  // Type-safe detection of rich data from Sankey clicks
  const hasRichData = Boolean(selectedData?._fullData)
  const isExpert = cardType === 'expert' || cardType === 'highway'
  const isRoute = cardType === 'route' || cardType === 'highway'

  // Safely extract label distribution for experts
  const categoryDistribution = hasRichData && isExpert && selectedData?.label_distribution
    ? selectedData.label_distribution as Record<string, number>
    : null

  // Extract per-axis category distributions (voice, scale, specificity, etc.)
  const axisDistributions = hasRichData && selectedData?.category_distributions
    ? selectedData.category_distributions as Record<string, Record<string, number>>
    : null

  // Reset tab when selectedData changes
  useEffect(() => {
    setActiveTab('details')
  }, [selectedData])

  if (!selectedData) {
    return (
      <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-300 p-8 text-center">
        <div className="text-gray-500">
          <ChartBarIcon style={{ width: '16px', height: '16px' }} className="mx-auto mb-2 text-gray-300" />
          <p className="font-medium">Click {cardType === 'expert' || cardType === 'highway' ? 'expert or route' : 'cluster or trajectory'}</p>
          <p className="text-sm mt-1">to see details here</p>
        </div>
      </div>
    )
  }

  const getCardTitle = () => {
    if (hasRichData) {
      switch (cardType) {
        case 'expert':
          return `Expert ${selectedData.name || selectedData.expertId || 'E?'}`
        case 'highway':
          return `Route ${selectedData.signature || 'L?E?→L?E?'}`
        case 'cluster':
          // For clusters, use the name directly (e.g., "L6C5")
          return selectedData.name || `Cluster ${selectedData.clusterId || 'C?'}`
        case 'route':
          return `Route ${selectedData.signature || 'L?C?→L?C?'}`
      }
    }
    // Fallback titles
    switch (cardType) {
      case 'expert': return `Expert ${selectedData.expertId || 'E?'}`
      case 'highway': return `Highway Route`
      case 'cluster': return `Cluster ${selectedData.clusterId || 'C?'}`
      case 'route': return `Trajectory Route`
    }
  }

  // Calculate statistics for expert cards with rich data
  const allLabels = [colorLabelA, colorLabelB].filter(Boolean)
  const analysis = categoryDistribution ? calculateStatisticalAnalysis(categoryDistribution, allLabels) : null


  return (
    <div className="bg-white rounded-xl shadow-md p-3 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">
            {getCardTitle()}
            {hasRichData && typeof selectedData.layer === 'number' && (
              <span className="text-xs text-gray-500 font-normal ml-1.5">Layer {selectedData.layer}</span>
            )}
          </h3>
        </div>
        {elementDescription && (
          <SparklesIcon className="w-4 h-4 text-purple-500" />
        )}
      </div>

      {/* Enhanced content for rich data */}
      {hasRichData ? (
        <>
          {/* Tabs */}
          <div className="flex border-b border-gray-200 mb-2">
            {[
              { key: 'details', label: 'Details' },
              { key: 'examples', label: 'Examples' },
              { key: 'ai', label: 'AI' }
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`px-2 py-1 text-xs font-medium border-b-2 ${
                  activeTab === tab.key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-auto">
            {activeTab === 'details' && (
              <div className="grid grid-cols-2 gap-2 h-full">
                {/* Left Column - Key Metrics */}
                <div className="space-y-2">
                  {/* Basic Stats Grid */}
                  <div className="grid grid-cols-2 gap-1.5">
                    <div className="bg-gray-50 px-2 py-1 rounded">
                      <p className="text-[10px] text-gray-500">Tokens</p>
                      <p className="text-xs font-semibold text-gray-900">
                        {typeof selectedData.token_count === 'number' ? selectedData.token_count : 0}
                      </p>
                    </div>
                    <div className="bg-gray-50 px-2 py-1 rounded">
                      <p className="text-[10px] text-gray-500">Coverage</p>
                      <p className="text-xs font-semibold text-gray-900">
                        {typeof selectedData.coverage === 'number' ? selectedData.coverage : 0}%
                      </p>
                    </div>

                    {isRoute && (
                      <>
                        <div className="bg-gray-50 px-2 py-1 rounded">
                          <p className="text-[10px] text-gray-500">Flow</p>
                          <p className="text-xs font-semibold text-gray-900">
                            {selectedData.value || selectedData.count || 0}
                          </p>
                        </div>
                        {typeof selectedData.avg_confidence === 'number' && (
                          <div className="bg-gray-50 px-2 py-1 rounded">
                            <p className="text-[10px] text-gray-500">Avg Confidence</p>
                            <p className="text-xs font-semibold text-gray-900">
                              {(selectedData.avg_confidence * 100).toFixed(1)}%
                            </p>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* Key Insights */}
                  {analysis && (
                    <div className="bg-blue-50 px-2 py-1.5 rounded">
                      <div className="space-y-0.5 text-[10px]">
                        <div className="flex justify-between">
                          <span className="text-blue-700">Diversity:</span>
                          <span className="font-medium text-blue-900">{analysis.diversity}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-blue-700">Dominant:</span>
                          <span className="font-medium text-blue-900 capitalize">{analysis.dominantCategory}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-blue-700">Concentration:</span>
                          <span className="font-medium text-blue-900">{analysis.concentrationRatio.toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Specialization */}
                  {selectedData.specialization && (
                    <div className="bg-gray-50 px-2 py-1 rounded">
                      <p className="text-[10px] text-gray-500">Specialization</p>
                      <p className="text-[11px] text-gray-700">{selectedData.specialization}</p>
                    </div>
                  )}
                </div>

                {/* Right Column - Category Breakdown & Statistics */}
                <div className="space-y-2">
                  {analysis && (
                    <>
                      {/* Label Distribution */}
                      <div>
                        <h4 className="font-medium text-gray-900 mb-1 text-[11px]">Label Distribution</h4>
                        <div className="space-y-1 max-h-48 overflow-y-auto">
                          {analysis.categoryStats.map(stat => (
                            <div key={stat.category}>
                              <div className="flex justify-between items-center">
                                <span className="text-[10px] font-medium text-gray-900 capitalize">{stat.category}</span>
                                <span className="text-[10px] text-gray-600">{stat.count} ({stat.percentage.toFixed(1)}%)</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-1">
                                <div
                                  className="bg-blue-500 h-1 rounded-full"
                                  style={{ width: `${Math.min(stat.percentage, 100)}%` }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Statistical Analysis */}
                      <div className="bg-blue-50 px-2 py-1.5 rounded">
                        <div className="space-y-0.5 text-[10px]">
                          <div className="flex justify-between">
                            <span className="text-blue-700">χ²:</span>
                            <span className="font-mono text-blue-900">{analysis.testStatistic.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-blue-700">p-value:</span>
                            <span className="font-mono text-blue-900">{analysis.pValue < 0.001 ? '<0.001' : analysis.pValue.toFixed(4)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-blue-700">Significant:</span>
                            <span className={`font-medium ${analysis.isSignificant ? 'text-green-600' : 'text-red-600'}`}>
                              {analysis.isSignificant ? 'Yes (p<0.05)' : 'No'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </>
                  )}

                  {/* Per-axis category distributions */}
                  {axisDistributions && Object.keys(axisDistributions).length > 0 && (
                    <div>
                      <h4 className="font-medium text-gray-900 mb-1 text-[11px]">Category Breakdown</h4>
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {Object.entries(axisDistributions).map(([axisId, dist]) => {
                          const total = Object.values(dist).reduce((s, v) => s + v, 0)
                          return (
                            <div key={axisId}>
                              <p className="text-[10px] font-medium text-gray-600 capitalize mb-0.5">{axisId}</p>
                              {Object.entries(dist)
                                .sort(([, a], [, b]) => b - a)
                                .map(([value, count]) => {
                                  const pct = total > 0 ? (count / total) * 100 : 0
                                  return (
                                    <div key={value} className="mb-0.5">
                                      <div className="flex justify-between items-center">
                                        <span className="text-[10px] text-gray-700 capitalize">{value}</span>
                                        <span className="text-[10px] text-gray-500">{count} ({pct.toFixed(0)}%)</span>
                                      </div>
                                      <div className="w-full bg-gray-200 rounded-full h-1">
                                        <div
                                          className="bg-indigo-400 h-1 rounded-full"
                                          style={{ width: `${Math.min(pct, 100)}%` }}
                                        />
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
                </div>

                {/* Cluster path for trajectory clicks */}
                {cardType === 'route' && clusterAssignments && Object.keys(clusterAssignments).length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <h4 className="text-[11px] font-semibold text-gray-600 mb-2">Cluster Path</h4>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(clusterAssignments)
                        .sort(([a], [b]) => Number(a) - Number(b))
                        .map(([layer, clusterId]) => (
                          <span key={layer} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px]">
                            L{layer} → C{clusterId}
                          </span>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'examples' && (() => {
              const examples = selectedData.tokens || selectedData.example_tokens || []
              return (
                <div>
                  {Array.isArray(examples) && examples.length > 0 ? (
                    <div className="space-y-0.5 max-h-72 overflow-y-auto">
                      {examples.slice(0, 10).map((token: any, index: number) => {
                        const tokenColor = token.label && colorLabelA && colorLabelB
                          ? getNodeColor({ [token.label]: 1 }, colorLabelA, colorLabelB, undefined, undefined, gradient)
                          : '#666666'
                        return (
                          <div key={token.probe_id || index} className="bg-gray-50 px-2 py-1 rounded">
                            <p className="text-[11px] text-gray-700 leading-snug">
                              {token.label && (
                                <span
                                  className="inline-block px-1 py-px text-[8px] font-medium rounded text-white capitalize mr-1 align-middle"
                                  style={{ backgroundColor: tokenColor }}
                                >
                                  {token.label}
                                </span>
                              )}
                              {token.input_text ? (
                                <SentenceHighlight
                                  text={token.input_text}
                                  targetWord={token.target_word || ''}
                                  color={tokenColor}
                                />
                              ) : (
                                <span className="text-gray-500">"{token.target_word || 'N/A'}"</span>
                              )}
                            </p>
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <p className="text-[11px] text-gray-500">No examples available</p>
                  )}
                </div>
              )
            })()}

            {activeTab === 'ai' && (
              <div>
                {elementDescription ? (
                  <div className="prose prose-sm max-w-none text-gray-800">
                    <ReactMarkdown>{elementDescription}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-[11px] text-gray-500 italic">
                    Run an element labeling step in the LLM panel to generate descriptions.
                  </p>
                )}
              </div>
            )}
          </div>
        </>
      ) : (
        // Basic display for simple data
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Population</span>
            <span className="font-medium text-gray-900">{selectedData.population || 'Unknown'}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Coverage</span>
            <span className="font-medium text-gray-900">{selectedData.coverage || '0'}%</span>
          </div>

          {selectedData.specialization && (
            <div className="pt-4 border-t border-gray-200">
              <span className="text-sm text-gray-600">Specialization</span>
              <p className="text-gray-900 mt-1">{selectedData.specialization}</p>
            </div>
          )}

          {selectedData.signature && (
            <div className="pt-4 border-t border-gray-200">
              <span className="text-sm text-gray-600">Route Signature</span>
              <p className="text-gray-900 font-mono text-sm mt-1">{selectedData.signature}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
