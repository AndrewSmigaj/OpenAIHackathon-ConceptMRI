import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import type { 
  SessionListItem, 
  SessionDetailResponse, 
  RouteAnalysisResponse,
  AnalyzeRoutesRequest,
  SankeyNode,
  SankeyLink
} from '../types/api'
import { apiClient } from '../api/client'
import { FlaskIcon, ChartBarIcon, SparklesIcon } from '../components/icons/Icons'
import * as echarts from 'echarts'
import WordFilterPanel, { type FilterState } from '../components/WordFilterPanel'
import FilteredWordDisplay from '../components/FilteredWordDisplay'
import SankeyChart from '../components/charts/SankeyChart'
import MultiSankeyView from '../components/charts/MultiSankeyView'
import SteppedTrajectoryPlot from '../components/charts/SteppedTrajectoryPlot'
import { getColorPreview, getNodeColor, type GradientScheme, GRADIENT_SCHEMES } from '../utils/colorBlending'
import SentenceHighlight from '../components/SentenceHighlight'
import { LAYER_RANGES } from '../constants/layerRanges'

/**
 * Convert frontend FilterState to backend filter_config format.
 * Empty sets mean "include all" (no filtering), so we return undefined.
 */
function convertFilterState(
  filterState: FilterState,
  sessionData?: SessionDetailResponse | null
): AnalyzeRoutesRequest['filter_config'] {
  const filterConfig: any = {};

  if (filterState.labels.size > 0) {
    filterConfig.labels = Array.from(filterState.labels);
  }

  return Object.keys(filterConfig).length > 0 ? filterConfig : undefined;
}

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

// @ts-ignore
import jStat from 'jStat'

function calculateStatisticalAnalysis(distribution: Record<string, number>): StatisticalAnalysis {
  const categories = Object.keys(distribution)
  const counts = Object.values(distribution)
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
  const expectedPerCategory = totalTokens / categories.length
  let testStatistic = 0
  
  categoryStats.forEach(stat => {
    const observed = stat.count
    const expected = expectedPerCategory
    testStatistic += Math.pow(observed - expected, 2) / expected
  })
  
  const degreesOfFreedom = categories.length - 1
  const pValue = 1 - jStat.chisquare.cdf(testStatistic, degreesOfFreedom)
  const isSignificant = pValue < 0.05
  const testType = 'Chi-square test vs uniform distribution'

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


interface LLMAnalysisProps {
  sessionId: string
  selectedContext?: string
  analysisType: 'expert' | 'latent'
  allRouteData?: Record<string, RouteAnalysisResponse | null> | null
  sessionData?: SessionDetailResponse | null
}

interface ContextSensitiveCardProps {
  cardType: 'expert' | 'highway' | 'cluster' | 'route'
  selectedData: any
  colorLabelA: string
  colorLabelB: string
  gradient: GradientScheme
}

function LLMAnalysisPanel({ sessionId, selectedContext, analysisType, allRouteData, sessionData }: LLMAnalysisProps) {
  const [apiKey, setApiKey] = useState('')
  const [userPrompt, setUserPrompt] = useState(`You are analyzing the "neural highways" of a Mixture of Experts language model - the pathways that different types of words take as they flow through 24 layers of processing.

**STRUCTURE YOUR ANALYSIS AS FOLLOWS:**

## 🏗️ NETWORK ARCHITECTURE DISCOVERY
Identify the major "hubs" and "highways" - which experts act as central processing stations vs specialized endpoints? Describe the overall flow pattern (broad→narrow→specialized, etc.).

## 🎭 THE GREAT SEMANTIC JOURNEY  
Trace how word meanings evolve from surface features (syntax, word length, first letters) in early layers to deep semantic fields (emotions, social roles, abstract concepts) in later layers. What's the most surprising transformation you observe?

## ⚡ ROUTING PHENOMENA & ANOMALIES
Highlight the most fascinating routing behaviors:
- Unexpected clustering patterns (like words starting with the same letter grouping together)
- "Semantic highways" where certain word types follow predictable paths  
- Bifurcation points where positive/negative sentiment separates
- Any "dead ends" or highly specialized micro-pipelines

## 🔮 THE HIDDEN LOGIC
What implicit "rules" is the model following? How does it decide which expert should handle which words? What does this reveal about how language models internally organize knowledge?

## 💎 DEMO-WORTHY INSIGHTS
Give me 3-5 "wow factor" findings that would blow someone's mind - the kind of discoveries that make people go "I had no idea neural networks were doing THAT internally!"

**CRITICAL: Avoid hallucination and over-interpretation**
- Only highlight patterns with substantial token flows (>20 tokens) or high confidence scores (>0.8)
- Distinguish between statistically significant patterns and random noise
- If a pattern could be coincidental, acknowledge the uncertainty
- Focus on robust, repeatable phenomena rather than cherry-picked examples
- Cite specific numbers (token counts, percentages, confidence scores) to ground your analysis

Use clear, engaging language with metaphors only when they genuinely clarify complex patterns. Focus on technical insights while keeping the analysis accessible and demo-ready.`)
  const [analysis, setAnalysis] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const handleAnalyze = async () => {
    if (!apiKey.trim()) {
      alert('Please enter your OpenAI API key')
      return
    }
    
    if (!allRouteData) {
      alert('No route data available. Please wait for data to load.')
      return
    }
    
    setIsAnalyzing(true)
    try {
      // Transform route data to windows format
      const windows = Object.values(allRouteData).filter(data => data !== null)
      
      const request = {
        session_id: sessionId,
        windows: windows,
        user_prompt: userPrompt,
        api_key: apiKey,
        provider: 'openai'
      }
      
      const response = await apiClient.generateLLMInsights(request)
      setAnalysis(response.narrative)
    } catch (error) {
      console.error('Analysis failed:', error)
      alert('Analysis failed: ' + (error instanceof Error ? error.message : 'Unknown error'))
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          LLM Analysis - {analysisType === 'expert' ? 'Expert Pathways' : 'Cluster Routes'}
        </h3>
        <FlaskIcon className="w-5 h-5 text-blue-600" />
      </div>
      
      {!analysis ? (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Analysis Prompt
            </label>
            <textarea
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              rows={12}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Describe what patterns you want the LLM to analyze..."
            />
            <p className="text-sm text-gray-500 mt-2">
              Edit this prompt to guide the LLM's analysis of the routing patterns
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              OpenAI API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="text-sm text-gray-500 mt-2">
              Your key is not stored and only used for this analysis request
            </p>
          </div>
          
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !apiKey.trim() || !userPrompt.trim() || !allRouteData}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            {isAnalyzing ? 'Analyzing...' : `Generate Analysis`}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
            <div className="text-gray-800 whitespace-pre-wrap text-sm leading-relaxed">
              {analysis}
            </div>
          </div>
          <button
            onClick={() => setAnalysis(null)}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            Generate New Analysis
          </button>
        </div>
      )}
    </div>
  )
}

function ContextSensitiveCard({ cardType, selectedData, colorLabelA, colorLabelB, gradient }: ContextSensitiveCardProps) {
  const [activeTab, setActiveTab] = useState<'details' | 'examples'>('details')
  const [isGeneratingLabel, setIsGeneratingLabel] = useState(false)
  const [customLabel, setCustomLabel] = useState<string>('')
  
  // Type-safe detection of rich data from Sankey clicks
  const hasRichData = Boolean(selectedData?._fullData)
  const isExpert = cardType === 'expert' || cardType === 'highway'
  const isRoute = cardType === 'route' || cardType === 'highway'

  // Safely extract label distribution for experts
  const categoryDistribution = hasRichData && isExpert && selectedData?.label_distribution
    ? selectedData.label_distribution as Record<string, number>
    : null

  // Reset tab when selectedData changes
  useEffect(() => {
    setActiveTab('details')
    setCustomLabel('')
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
  const analysis = categoryDistribution ? calculateStatisticalAnalysis(categoryDistribution) : null

  const handleGenerateLabel = async () => {
    setIsGeneratingLabel(true)
    // TODO: Implement LLM labeling API call
    setTimeout(() => {
      setCustomLabel(`AI-generated label for ${getCardTitle()}`)
      setIsGeneratingLabel(false)
    }, 2000)
  }

  return (
    <div className="bg-white rounded-xl shadow-md p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{getCardTitle()}</h3>
          {hasRichData && typeof selectedData.layer === 'number' && (
            <p className="text-sm text-gray-500">Layer {selectedData.layer}</p>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <ChartBarIcon style={{ width: '12px', height: '12px' }} className="text-blue-600" />
          <button
            onClick={handleGenerateLabel}
            disabled={isGeneratingLabel}
            className="p-1 text-purple-600 hover:text-purple-700 disabled:text-gray-400 disabled:cursor-not-allowed"
            title="Generate LLM Label"
          >
            <SparklesIcon className={`w-4 h-4 ${isGeneratingLabel ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Custom Label if available */}
      {customLabel && (
        <div className="mb-4 p-3 bg-purple-50 rounded-lg border border-purple-200">
          <p className="text-sm font-medium text-purple-800">LLM Label:</p>
          <p className="text-sm text-purple-700 mt-1">{customLabel}</p>
        </div>
      )}

      {/* Enhanced content for rich data */}
      {hasRichData ? (
        <>
          {/* Tabs */}
          <div className="flex border-b border-gray-200 mb-4">
            {[
              { key: 'details', label: 'Details' },
              { key: 'examples', label: 'Examples' }
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`px-3 py-2 text-sm font-medium border-b-2 ${
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
              <div className="grid grid-cols-2 gap-4 h-full">
                {/* Left Column - Key Metrics */}
                <div className="space-y-3">
                  {/* Basic Stats Grid */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-gray-50 p-2 rounded-lg">
                      <p className="text-xs text-gray-500">Total Tokens</p>
                      <p className="text-sm font-semibold text-gray-900">
                        {typeof selectedData.token_count === 'number' ? selectedData.token_count : 0}
                      </p>
                    </div>
                    <div className="bg-gray-50 p-2 rounded-lg">
                      <p className="text-xs text-gray-500">Coverage</p>
                      <p className="text-sm font-semibold text-gray-900">
                        {typeof selectedData.coverage === 'number' ? selectedData.coverage : 0}%
                      </p>
                    </div>
                    
                    {isRoute && (
                      <>
                        <div className="bg-gray-50 p-2 rounded-lg">
                          <p className="text-xs text-gray-500">Flow Volume</p>
                          <p className="text-sm font-semibold text-gray-900">
                            {selectedData.value || selectedData.count || 0}
                          </p>
                        </div>
                        {typeof selectedData.avg_confidence === 'number' && (
                          <div className="bg-gray-50 p-2 rounded-lg">
                            <p className="text-xs text-gray-500">Avg Confidence</p>
                            <p className="text-sm font-semibold text-gray-900">
                              {(selectedData.avg_confidence * 100).toFixed(1)}%
                            </p>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* Key Insights */}
                  {analysis && (
                    <div className="bg-blue-50 p-3 rounded-lg">
                      <h4 className="font-medium text-blue-900 mb-2 text-sm">Key Insights</h4>
                      <div className="space-y-1 text-xs">
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
                    <div className="bg-gray-50 p-3 rounded-lg">
                      <p className="text-xs text-gray-500 mb-1">Specialization</p>
                      <p className="text-sm text-gray-700">{selectedData.specialization}</p>
                    </div>
                  )}
                </div>

                {/* Right Column - Category Breakdown & Statistics */}
                <div className="space-y-3">
                  {analysis && (
                    <>
                      {/* Label Distribution */}
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3 text-sm">Label Distribution</h4>
                        <div className="space-y-2 max-h-60 overflow-y-auto">
                          {analysis.categoryStats.map(stat => (
                            <div key={stat.category}>
                              <div className="flex justify-between items-center mb-1">
                                <span className="text-xs font-medium text-gray-900 capitalize">{stat.category}</span>
                                <span className="text-xs text-gray-600">{stat.percentage.toFixed(1)}%</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-1.5">
                                <div
                                  className="bg-blue-500 h-1.5 rounded-full"
                                  style={{ width: `${Math.min(stat.percentage, 100)}%` }}
                                />
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                {stat.count} tokens
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Statistical Analysis */}
                      <div className="bg-blue-50 p-3 rounded-lg">
                        <h4 className="font-medium text-blue-900 mb-2 text-sm">Statistical Analysis</h4>
                        <div className="space-y-1 text-xs">
                          <div className="flex justify-between">
                            <span className="text-blue-700">Test:</span>
                            <span className="text-blue-900">{analysis.testType}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-blue-700">Test statistic:</span>
                            <span className="font-mono text-blue-900">{analysis.testStatistic.toFixed(3)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-blue-700">p-value:</span>
                            <span className="font-mono text-blue-900">{analysis.pValue < 0.001 ? '<0.001' : analysis.pValue.toFixed(4)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-blue-700">Significant (p &lt; 0.05):</span>
                            <span className={`font-medium ${analysis.isSignificant ? 'text-green-600' : 'text-red-600'}`}>
                              {analysis.isSignificant ? 'Yes' : 'No'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'examples' && (() => {
              const examples = selectedData.tokens || selectedData.example_tokens || []
              return (
                <div className="space-y-4">
                  <h4 className="font-medium text-gray-900">Examples</h4>
                  {Array.isArray(examples) && examples.length > 0 ? (
                    <div className="space-y-3 max-h-80 overflow-y-auto">
                      {examples.slice(0, 10).map((token: any, index: number) => {
                        const tokenColor = token.label && colorLabelA && colorLabelB
                          ? getNodeColor({ [token.label]: 1 }, colorLabelA, colorLabelB, undefined, undefined, gradient)
                          : '#666666'
                        return (
                          <div key={token.probe_id || index} className="bg-gray-50 p-3 rounded-lg">
                            <div className="flex items-center space-x-2 mb-1">
                              {token.label && (
                                <span
                                  className="px-1.5 py-0.5 text-[10px] font-medium rounded-full text-white capitalize"
                                  style={{ backgroundColor: tokenColor }}
                                >
                                  {token.label}
                                </span>
                              )}
                            </div>
                            {token.input_text ? (
                              <p className="text-xs text-gray-700 leading-relaxed">
                                <SentenceHighlight
                                  text={token.input_text}
                                  targetWord={token.target_word || ''}
                                  color={tokenColor}
                                />
                              </p>
                            ) : (
                              <span className="text-xs text-gray-500">"{token.target_word || 'N/A'}"</span>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No examples available</p>
                  )}
                </div>
              )
            })()}
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

interface ColorControlsProps {
  colorLabelA: string
  colorLabelB: string
  gradient: GradientScheme
  onGradientChange: (gradient: GradientScheme) => void
}

function ColorControls({
  colorLabelA,
  colorLabelB,
  gradient,
  onGradientChange
}: ColorControlsProps) {
  const colorPreview = getColorPreview(colorLabelA, colorLabelB, undefined, undefined, gradient)

  return (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900">Color Controls</h4>

      {/* Show current color axis */}
      {colorLabelA && colorLabelB ? (
        <div className="text-sm text-gray-700">
          Coloring by: <span className="font-medium">{colorLabelA}</span> vs <span className="font-medium">{colorLabelB}</span>
        </div>
      ) : (
        <div className="text-sm text-gray-500 italic">
          Run analysis to detect color axis from data
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Gradient
        </label>
        <select
          value={gradient}
          onChange={(e) => onGradientChange(e.target.value as GradientScheme)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          {Object.entries(GRADIENT_SCHEMES).map(([key, scheme]) => (
            <option key={key} value={key}>{scheme.name}</option>
          ))}
        </select>
      </div>

      {/* Color Preview */}
      {colorLabelA && colorLabelB && (
        <div className="pt-2 border-t border-gray-200">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Color Preview
          </label>
          <div className="grid grid-cols-3 gap-2 text-xs">
            {Object.entries(colorPreview).map(([label, color]) => (
              <div key={label} className="flex items-center space-x-2">
                <div
                  className="rounded border border-gray-300 flex-shrink-0"
                  style={{
                    backgroundColor: color,
                    width: '20px',
                    height: '20px',
                    minWidth: '20px',
                    minHeight: '20px'
                  }}
                />
                <span className="text-gray-600 truncate">{label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ExpertHighwaysTab({
  sessionIds,
  sessionData,
  filterState,
  colorLabelA,
  colorLabelB,
  gradient,
  topRoutes,
  selectedRange,
  onRangeChange,
  showAllRoutes,
  onRouteDataLoaded
}: {
  sessionIds: string[]
  sessionData: SessionDetailResponse | null
  filterState: FilterState
  colorLabelA: string
  colorLabelB: string
  gradient: GradientScheme
  topRoutes: number
  selectedRange: string
  onRangeChange: (range: string) => void
  showAllRoutes: boolean
  onRouteDataLoaded: (routeDataMap: Record<string, RouteAnalysisResponse | null>) => void
}) {
  const [selectedCard, setSelectedCard] = useState<{ type: 'expert' | 'highway', data: any } | null>(null)
  const [runAnalysis, setRunAnalysis] = useState<(() => void) | null>(null)

  const handleSankeyClick = (elementType: 'expert' | 'route', data: any) => {
    setSelectedCard({ 
      type: elementType === 'expert' ? 'expert' : 'highway', 
      data 
    })
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-4 h-full">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Expert Routing Pathways</h3>
          <p className="text-xs text-gray-600 mt-1">Click experts or routes to see details</p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => runAnalysis?.()}
            disabled={!runAnalysis}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Run Analysis
          </button>
          <ChartBarIcon style={{ width: '12px', height: '12px' }} className="text-blue-600" />
        </div>
      </div>
      
      {/* Multi-Sankey Route Analysis Visualization */}
      <div className="bg-gray-50 rounded-lg p-6">
        <MultiSankeyView
          sessionIds={sessionIds}
          sessionData={sessionData}
          filterState={filterState}
          colorLabelA={colorLabelA}
          colorLabelB={colorLabelB}
          gradient={gradient}
          showAllRoutes={showAllRoutes}
          topRoutes={topRoutes}
          selectedRange={selectedRange}
          onRangeChange={onRangeChange}
          onNodeClick={(data) => handleSankeyClick('expert', data)}
          onLinkClick={(data) => handleSankeyClick('route', data)}
          onRouteDataLoaded={onRouteDataLoaded}
          mode="expert"
          manualTrigger={true}
          onAnalysisReady={useCallback((analysisFunction) => setRunAnalysis(() => analysisFunction), [])}
        />
      </div>

      {/* Context-Sensitive Card integrated */}
      {selectedCard && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <ContextSensitiveCard
            cardType={selectedCard.type}
            selectedData={selectedCard.data}
            colorLabelA={colorLabelA}
            colorLabelB={colorLabelB}
            gradient={gradient}
          />
        </div>
      )}
    </div>
  )
}

function LatentSpaceTab({
  sessionIds,
  sessionData,
  filterState,
  colorLabelA,
  colorLabelB,
  gradient,
  selectedRange,
  onRangeChange,
  layerClusterCounts,
  clusteringMethod,
  reductionDimensions,
  embeddingSource,
  reductionMethod,
  useAllLayersSameClusters,
  setUseAllLayersSameClusters,
  globalClusterCount,
  setGlobalClusterCount
}: {
  sessionIds: string[]
  sessionData: SessionDetailResponse | null
  filterState: FilterState
  colorLabelA: string
  colorLabelB: string
  gradient: GradientScheme
  selectedRange: string
  onRangeChange: (range: string) => void
  layerClusterCounts: {[key: number]: number}
  clusteringMethod: string
  reductionDimensions: number
  embeddingSource: string
  reductionMethod: string
  useAllLayersSameClusters: boolean
  setUseAllLayersSameClusters: (value: boolean) => void
  globalClusterCount: number
  setGlobalClusterCount: (value: number) => void
}) {
  const [selectedCard, setSelectedCard] = useState<{ type: 'cluster' | 'route', data: any } | null>(null)
  const [runAnalysis, setRunAnalysis] = useState<(() => void) | null>(null)
  const [runTrajectoryAnalysis, setRunTrajectoryAnalysis] = useState<(() => void) | null>(null)

  // Memoize layers array to prevent infinite re-renders
  const memoizedLayers = useMemo(() => {
    return LAYER_RANGES[selectedRange as keyof typeof LAYER_RANGES]?.windows.map(w => w.layers).flat() || []
  }, [selectedRange])

  const handleVisualizationClick = useCallback((elementType: 'cluster' | 'trajectory', data: any) => {
    setSelectedCard({ 
      type: elementType === 'cluster' ? 'cluster' : 'route', 
      data 
    })
  }, [])

  const handleSankeyAnalysisReady = useCallback((analysisFunction: () => void) => {
    setRunAnalysis(() => analysisFunction)
  }, [])

  const handleTrajectoryAnalysisReady = useCallback((analysisFunction: () => void) => {
    setRunTrajectoryAnalysis(() => analysisFunction)
  }, [])

  // Memoize clusteringConfig to prevent infinite re-renders
  const memoizedClusteringConfig = useMemo(() => {
    let effectiveLayerClusterCounts;
    
    if (useAllLayersSameClusters) {
      // Use the global cluster count for all current window layers
      effectiveLayerClusterCounts = {};
      memoizedLayers.forEach(layer => {
        effectiveLayerClusterCounts[layer] = globalClusterCount;
      });
    } else {
      // Use the per-layer configuration
      effectiveLayerClusterCounts = layerClusterCounts;
    }
    
    return {
      reduction_dimensions: reductionDimensions,
      clustering_method: clusteringMethod,
      layer_cluster_counts: effectiveLayerClusterCounts,
      embedding_source: embeddingSource,
      reduction_method: reductionMethod
    };
  }, [reductionDimensions, clusteringMethod, layerClusterCounts, useAllLayersSameClusters, globalClusterCount, memoizedLayers, embeddingSource, reductionMethod])

  return (
    <div className="bg-white rounded-xl shadow-sm p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Latent Space Analysis</h3>
          <p className="text-xs text-gray-600 mt-1">Cluster trajectories and stepped trajectory visualization</p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => {
              runAnalysis?.()
              runTrajectoryAnalysis?.()
            }}
            disabled={!runAnalysis || !runTrajectoryAnalysis}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Run Analysis
          </button>
          <ChartBarIcon style={{ width: '12px', height: '12px' }} className="text-blue-600" />
        </div>
      </div>
      
      <div className="flex-1 overflow-auto">
        {/* Trajectory Sankey - Clusters and Paths */}
        <div className="bg-gray-50 rounded-lg p-6 mb-4">
          <MultiSankeyView
            sessionIds={sessionIds}
            sessionData={sessionData}
            filterState={filterState}
            colorLabelA={colorLabelA}
            colorLabelB={colorLabelB}
            gradient={gradient}
            showAllRoutes={false}
            topRoutes={20}
            selectedRange={selectedRange}
            onRangeChange={onRangeChange}
            onNodeClick={(data) => handleVisualizationClick('cluster', data)}
            onLinkClick={(data) => handleVisualizationClick('trajectory', data)}
            mode="cluster"
            manualTrigger={true}
            onAnalysisReady={handleSankeyAnalysisReady}
            clusteringConfig={memoizedClusteringConfig}
          />
        </div>

        {/* Stepped Trajectory Plot */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-4">
          <SteppedTrajectoryPlot
            sessionIds={sessionIds}
            layers={memoizedLayers}
            colorLabelA={colorLabelA}
            colorLabelB={colorLabelB}
            gradient={gradient}
            source={embeddingSource}
            method={reductionMethod}
            sessionData={sessionData}
            filterConfig={convertFilterState(filterState, sessionData)}
            height={400}
            maxTrajectories={100}
            manualTrigger={true}
            onAnalysisReady={handleTrajectoryAnalysisReady}
            onPointClick={useCallback((info: { probe_id: string; target: string; label?: string }) => {
              // Look up the full sentence from session data
              const sentence = sessionData?.sentences?.find(s => s.probe_id === info.probe_id)
              if (sentence) {
                setSelectedCard({
                  type: 'route',
                  data: {
                    _fullData: sentence,
                    name: info.target,
                    label: info.label,
                    tokens: [sentence],
                    example_tokens: [sentence],
                    signature: `Trajectory: ${info.probe_id.slice(0, 8)}`,
                  }
                })
              }
            }, [sessionData])}
          />
        </div>

        {/* Context-Sensitive Card integrated */}
        {selectedCard && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <ContextSensitiveCard
              cardType={selectedCard.type}
              selectedData={selectedCard.data}
              colorLabelA={colorLabelA}
              colorLabelB={colorLabelB}
              gradient={gradient}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default function ExperimentPage() {
  const { id } = useParams<{ id: string }>()
  const [selectedSessions, setSelectedSessions] = useState<string[]>([])
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [mergedSessionDetails, setMergedSessionDetails] = useState<SessionDetailResponse | null>(null)
  const [activeTab, setActiveTab] = useState<'expert' | 'latent'>('expert')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterState, setFilterState] = useState<FilterState>({
    labels: new Set()
  })

  // Color controls — single axis defined by two label strings from backend available_axes
  const [colorLabelA, setColorLabelA] = useState<string>('')
  const [colorLabelB, setColorLabelB] = useState<string>('')
  const [gradient, setGradient] = useState<GradientScheme>('red-blue')
  const [windowLayers, setWindowLayers] = useState<number[]>([0, 1])
  const [selectedRange, setSelectedRange] = useState<string>('range1')
  
  // Expert tab controls
  const [topRoutes, setTopRoutes] = useState(10)
  const [showAllRoutes, setShowAllRoutes] = useState(false)
  
  // Latent tab controls
  const [layerClusterCounts, setLayerClusterCounts] = useState<{[key: number]: number}>({})
  const [clusteringMethod, setClusteringMethod] = useState('kmeans')
  const [reductionDims, setReductionDims] = useState(3)
  const [embeddingSource, setEmbeddingSource] = useState<string>('expert_output')
  const [reductionMethod, setReductionMethod] = useState<string>('pca')
  const [customDimensions, setCustomDimensions] = useState(15)
  const [useCustomDimensions, setUseCustomDimensions] = useState(false)
  
  // Cluster configuration mode
  const [useAllLayersSameClusters, setUseAllLayersSameClusters] = useState(true)  // Default to "same for all"
  const [globalClusterCount, setGlobalClusterCount] = useState(4)  // Default to 4 clusters

  // LLM Insights state
  const [currentRouteData, setCurrentRouteData] = useState<Record<string, RouteAnalysisResponse | null> | null>(null)

  // Derive available labels from route analysis available_axes
  const availableLabels = useMemo(() => {
    if (!currentRouteData) return []
    const labels = new Set<string>()
    for (const data of Object.values(currentRouteData)) {
      if (data?.available_axes) {
        for (const axis of data.available_axes) {
          if (axis.id === 'label') {
            labels.add(axis.label_a)
            labels.add(axis.label_b)
          }
        }
      }
    }
    return Array.from(labels)
  }, [currentRouteData])

  // Auto-detect color axis from route analysis available_axes
  const handleRouteDataLoaded = useCallback((routeDataMap: Record<string, RouteAnalysisResponse | null>) => {
    setCurrentRouteData(routeDataMap)
    // Pick color labels from the first response that has available_axes
    if (!colorLabelA || !colorLabelB) {
      for (const data of Object.values(routeDataMap)) {
        if (data?.available_axes && data.available_axes.length > 0) {
          const axis = data.available_axes[0]
          setColorLabelA(axis.label_a)
          setColorLabelB(axis.label_b)
          break
        }
      }
    }
  }, [colorLabelA, colorLabelB])

  // Helper to update cluster counts when window changes
  const updateWindowLayers = (newWindow: number[]) => {
    setWindowLayers(newWindow)
    // Initialize cluster counts for new layers if not set
    const newCounts = { ...layerClusterCounts }
    newWindow.forEach(layer => {
      if (!(layer in newCounts)) {
        newCounts[layer] = 4 // default cluster count
      }
    })
    setLayerClusterCounts(newCounts)
  }

  useEffect(() => {
    loadSessions()
  }, [])

  useEffect(() => {
    if (selectedSessions.length > 0) {
      loadAndMergeSessions()
    } else {
      setMergedSessionDetails(null)
    }
  }, [selectedSessions])

  const loadAndMergeSessions = async () => {
    try {
      const details = await Promise.all(
        selectedSessions.map(id => apiClient.getSessionDetails(id))
      )

      if (details.length === 1) {
        setMergedSessionDetails(details[0])
        return
      }

      // Merge labels by union across sessions
      const mergedLabels = new Set<string>()
      for (const d of details) {
        (d.labels || []).forEach((l: string) => mergedLabels.add(l))
      }

      // Merge sentences across sessions
      const mergedSentences = details.flatMap(d => d.sentences || [])

      setMergedSessionDetails({
        manifest: details[0].manifest,
        data_lake_paths: details[0].data_lake_paths,
        labels: Array.from(mergedLabels),
        target_word: details[0].target_word,
        sentences: mergedSentences.length > 0 ? mergedSentences : undefined
      })
    } catch (err) {
      console.error('Failed to load session details:', err)
      setMergedSessionDetails(null)
    }
  }

  const loadSessions = async () => {
    try {
      setLoading(true)
      setError(null)
      const sessionsData = await apiClient.listSessions()
      setSessions(sessionsData)
      
      // Filter to only completed sessions for analysis
      const completedSessions = sessionsData.filter(s => s.state === 'completed')
      
      // Only auto-select if session ID is in URL and exists
      if (id && completedSessions.find((s: SessionListItem) => s.session_id === id)) {
        setSelectedSessions([id])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions')
      console.error('Failed to load sessions:', err)
    } finally {
      setLoading(false)
    }
  }

  const selectedSessionData = selectedSessions.length > 0 ? sessions.find(s => s.session_id === selectedSessions[0]) : undefined

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading experiment data...</p>
        </div>
      </div>
    )
  }

  if (error || sessions.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <FlaskIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">
            {error ? 'Error Loading Data' : 'No Probe Sessions'}
          </h2>
          <p className="text-gray-600 mb-6">
            {error || 'Create a probe session first to analyze experiments.'}
          </p>
          {error ? (
            <button
              onClick={loadSessions}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors shadow-sm"
            >
              Retry
            </button>
          ) : (
            <a
              href="/"
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors shadow-sm"
            >
              Go to Workspace
            </a>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="px-8 py-6">
          <h1 className="text-2xl font-bold text-gray-900">Concept MRI Experiment</h1>
          <p className="text-sm text-gray-600">Analyze MoE routing patterns and latent trajectories</p>
        </div>
      </div>

      <div className="flex h-[calc(100vh-88px)]">
        {/* Left Sidebar - Session, Tabs, Controls */}
        <div className="bg-white shadow-sm border-r flex flex-col sidebar-narrow">
          {/* Session Selector — checkbox list for multi-session */}
          <div className="p-2 border-b">
            <h3 className="text-xs font-semibold text-gray-700 mb-1">Sessions</h3>
            <div className="max-h-32 overflow-y-auto space-y-1">
              {sessions.filter(s => s.state === 'completed').map((session) => (
                <label key={session.session_id} className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedSessions.includes(session.session_id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedSessions(prev => [...prev, session.session_id])
                      } else {
                        setSelectedSessions(prev => prev.filter(id => id !== session.session_id))
                      }
                    }}
                    className="w-3 h-3 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="ml-1.5 text-xs text-gray-700 truncate">{session.session_name}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="p-3 border-b">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Analysis Type</h3>
            <div className="space-y-1">
              <button
                onClick={() => setActiveTab('expert')}
                className={`w-full flex items-center px-3 py-2 rounded-md text-sm transition-colors ${
                  activeTab === 'expert'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                }`}
              >
                <ChartBarIcon style={{ width: '10px', height: '10px' }} className="mr-1 flex-shrink-0" />
                <div className="text-left min-w-0">
                  <p className="font-medium text-xs">Expert Highways</p>
                </div>
              </button>
              
              <button
                onClick={() => setActiveTab('latent')}
                className={`w-full flex items-center px-3 py-2 rounded-md text-sm transition-colors ${
                  activeTab === 'latent'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                }`}
              >
                <ChartBarIcon style={{ width: '10px', height: '10px' }} className="mr-1 flex-shrink-0" />
                <div className="text-left min-w-0">
                  <p className="font-medium text-xs">Latent Space</p>
                </div>
              </button>
            </div>
          </div>

          {/* Controls Section */}
          {selectedSessions.length > 0 && (
            <div className="p-3 border-b flex-1">
              <h3 className="text-xs font-semibold text-gray-900 mb-2">Controls</h3>
              
              <div className="space-y-4">
                {/* Shared Controls */}
                <div className="border-t border-gray-200 pt-3 mt-3">
                  <ColorControls
                    colorLabelA={colorLabelA}
                    colorLabelB={colorLabelB}
                    gradient={gradient}
                    onGradientChange={setGradient}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Window Layers</label>
                  <select
                    value={windowLayers.join(',')}
                    onChange={(e) => {
                      const layers = e.target.value.split(',').map(Number)
                      updateWindowLayers(layers)
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <optgroup label="2-Layer Windows">
                      <option value="0,1">Layers 0→1</option>
                      <option value="1,2">Layers 1→2</option>
                      <option value="2,3">Layers 2→3</option>
                      <option value="3,4">Layers 3→4</option>
                      <option value="4,5">Layers 4→5</option>
                      <option value="5,6">Layers 5→6</option>
                      <option value="6,7">Layers 6→7</option>
                      <option value="7,8">Layers 7→8</option>
                      <option value="8,9">Layers 8→9</option>
                      <option value="9,10">Layers 9→10</option>
                      <option value="10,11">Layers 10→11</option>
                      <option value="11,12">Layers 11→12</option>
                      <option value="12,13">Layers 12→13</option>
                      <option value="13,14">Layers 13→14</option>
                      <option value="14,15">Layers 14→15</option>
                      <option value="15,16">Layers 15→16</option>
                      <option value="16,17">Layers 16→17</option>
                      <option value="17,18">Layers 17→18</option>
                      <option value="18,19">Layers 18→19</option>
                      <option value="19,20">Layers 19→20</option>
                      <option value="20,21">Layers 20→21</option>
                      <option value="21,22">Layers 21→22</option>
                      <option value="22,23">Layers 22→23</option>
                    </optgroup>
                    <optgroup label="3-Layer Windows">
                      <option value="0,1,2">Layers 0→1→2</option>
                      <option value="1,2,3">Layers 1→2→3</option>
                      <option value="2,3,4">Layers 2→3→4</option>
                      <option value="3,4,5">Layers 3→4→5</option>
                      <option value="4,5,6">Layers 4→5→6</option>
                      <option value="5,6,7">Layers 5→6→7</option>
                      <option value="6,7,8">Layers 6→7→8</option>
                      <option value="7,8,9">Layers 7→8→9</option>
                      <option value="8,9,10">Layers 8→9→10</option>
                      <option value="9,10,11">Layers 9→10→11</option>
                      <option value="10,11,12">Layers 10→11→12</option>
                      <option value="11,12,13">Layers 11→12→13</option>
                      <option value="12,13,14">Layers 12→13→14</option>
                      <option value="13,14,15">Layers 13→14→15</option>
                      <option value="14,15,16">Layers 14→15→16</option>
                      <option value="15,16,17">Layers 15→16→17</option>
                      <option value="16,17,18">Layers 16→17→18</option>
                      <option value="17,18,19">Layers 17→18→19</option>
                      <option value="18,19,20">Layers 18→19→20</option>
                      <option value="19,20,21">Layers 19→20→21</option>
                      <option value="20,21,22">Layers 20→21→22</option>
                      <option value="21,22,23">Layers 21→22→23</option>
                    </optgroup>
                  </select>
                </div>

                {/* Expert Tab Controls */}
                {activeTab === 'expert' && (
                  <>
                    <div>
                      <label className="flex items-center space-x-2 text-sm font-medium text-gray-700 mb-2">
                        <input
                          type="checkbox"
                          checked={showAllRoutes}
                          onChange={(e) => setShowAllRoutes(e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span>Show All Routes</span>
                      </label>
                      <p className="text-xs text-gray-500 mb-3">
                        {showAllRoutes ? 'Displaying all available routes' : `Limited to top ${topRoutes} routes`}
                      </p>
                    </div>
                    
                    {!showAllRoutes && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Top Routes</label>
                        <input
                          type="number"
                          value={topRoutes}
                          onChange={(e) => setTopRoutes(parseInt(e.target.value))}
                          min="5"
                          max="100"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    )}
                  </>
                )}

                {/* Latent Tab Controls */}
                {activeTab === 'latent' && (
                  <>
                    {/* Embedding Source + Reduction Method */}
                    <div className="border-t border-gray-200 pt-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">Embedding Source</h4>
                      <select
                        value={embeddingSource}
                        onChange={(e) => setEmbeddingSource(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="expert_output">Expert Output</option>
                        <option value="residual_stream">Residual Stream</option>
                      </select>
                    </div>

                    <div className="border-t border-gray-200 pt-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">Reduction Method</h4>
                      <select
                        value={reductionMethod}
                        onChange={(e) => setReductionMethod(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="pca">PCA</option>
                        <option value="umap">UMAP</option>
                      </select>
                    </div>

                    <div className="border-t border-gray-200 pt-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">Reduction Dimensions</h4>
                      <div className="mb-4">
                        <div className="space-y-2">
                          {[2, 3, 5, 10].map(dim => (
                            <label key={dim} className="flex items-center">
                              <input
                                type="radio"
                                name="reductionDims"
                                checked={reductionDims === dim && !useCustomDimensions}
                                onChange={() => {
                                  setReductionDims(dim)
                                  setUseCustomDimensions(false)
                                }}
                                className="mr-2"
                              />
                              <span className="text-sm">
                                {dim}D - {
                                  dim === 2 ? 'Major axes' :
                                  dim === 3 ? '+ depth' :
                                  dim === 5 ? 'Fine structure' :
                                  'Detailed patterns'
                                }
                              </span>
                            </label>
                          ))}
                          <label className="flex items-center">
                            <input
                              type="radio"
                              name="reductionDims"
                              checked={useCustomDimensions}
                              onChange={() => setUseCustomDimensions(true)}
                              className="mr-2"
                            />
                            <span className="text-sm mr-2">Custom:</span>
                            <input
                              type="number"
                              value={customDimensions}
                              onChange={(e) => setCustomDimensions(parseInt(e.target.value) || 1)}
                              onFocus={() => setUseCustomDimensions(true)}
                              min="1"
                              max="128"
                              className="w-16 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                            />
                            <span className="text-sm ml-1">(1-128)</span>
                          </label>
                        </div>
                      </div>
                    </div>

                    <div className="border-t border-gray-200 pt-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">Per-Layer Clustering</h4>
                      {(() => {
                        const currentRange = selectedRange as keyof typeof LAYER_RANGES
                        const rangeDef = LAYER_RANGES[currentRange]
                        if (!rangeDef) return null
                        
                        // Get all unique layers from the current range
                        const allLayers = new Set<number>()
                        rangeDef.windows.forEach(window => {
                          window.layers.forEach(layer => allLayers.add(layer))
                        })
                        
                        return Array.from(allLayers).sort((a, b) => a - b).map((layer) => (
                          <div key={layer} className="mb-3">
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Layer {layer} Clusters (K)
                            </label>
                            <input
                              type="number"
                              value={layerClusterCounts[layer] || 4}
                              onChange={(e) => {
                                const newCounts = { ...layerClusterCounts }
                                newCounts[layer] = parseInt(e.target.value)
                                setLayerClusterCounts(newCounts)
                              }}
                              min="2"
                              max="20"
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                          </div>
                        ))
                      })()}
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Clustering Method</label>
                      <select
                        value={clusteringMethod}
                        onChange={(e) => setClusteringMethod(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="kmeans">K-Means</option>
                        <option value="hierarchical">Hierarchical</option>
                        <option value="dbscan">DBSCAN</option>
                      </select>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Session Stats */}
          {selectedSessionData && (
            <div className="p-4">
              <h3 className="text-xs font-semibold text-gray-700 mb-2">Session Info</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-600">Probes</span>
                  <span className="font-medium text-sm text-gray-900">{selectedSessionData.probe_count}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-600">Status</span>
                  <span className="font-medium text-sm text-gray-900">{selectedSessionData.state}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Main Content Area - 3 Column Layout */}
        <div className="flex-1 flex">
          {selectedSessions.length > 0 ? (
            <>
              {/* Middle Column - Word Lists */}
              <div className="bg-gray-50 border-r p-4 space-y-4 word-panel-narrow">
                {mergedSessionDetails && (
                  <>
                    <WordFilterPanel
                      sessionData={mergedSessionDetails}
                      selectedFilters={filterState}
                      onFiltersChange={setFilterState}
                      isLoading={!mergedSessionDetails}
                    />

                    <FilteredWordDisplay
                      sessionData={mergedSessionDetails}
                      filterState={filterState}
                      isLoading={!mergedSessionDetails}
                      colorLabelA={colorLabelA}
                      colorLabelB={colorLabelB}
                      gradient={gradient}
                    />
                  </>
                )}
              </div>

              {/* Right Column - Visualization + LLM Analysis */}
              <div className="flex-1 flex flex-col">
                <div className="flex-1 p-4">
                  {activeTab === 'expert' && (
                    <ExpertHighwaysTab
                      sessionIds={selectedSessions}
                      sessionData={mergedSessionDetails}
                      filterState={filterState}
                      colorLabelA={colorLabelA}
                      colorLabelB={colorLabelB}
                      gradient={gradient}
                      topRoutes={topRoutes}
                      selectedRange={selectedRange}
                      onRangeChange={setSelectedRange}
                      showAllRoutes={showAllRoutes}
                      onRouteDataLoaded={handleRouteDataLoaded}
                    />
                  )}
                  {activeTab === 'latent' && (
                    <LatentSpaceTab
                      sessionIds={selectedSessions}
                      sessionData={mergedSessionDetails}
                      filterState={filterState}
                      colorLabelA={colorLabelA}
                      colorLabelB={colorLabelB}
                      gradient={gradient}
                      selectedRange={selectedRange}
                      onRangeChange={setSelectedRange}
                      layerClusterCounts={layerClusterCounts}
                      clusteringMethod={clusteringMethod}
                      reductionDimensions={useCustomDimensions ? customDimensions : reductionDims}
                      embeddingSource={embeddingSource}
                      reductionMethod={reductionMethod}
                      useAllLayersSameClusters={useAllLayersSameClusters}
                      setUseAllLayersSameClusters={setUseAllLayersSameClusters}
                      globalClusterCount={globalClusterCount}
                      setGlobalClusterCount={setGlobalClusterCount}
                    />
                  )}
                </div>

                {/* LLM Analysis Panel - Below Visualization */}
                <div className="border-t bg-white p-4">
                  <LLMAnalysisPanel
                    sessionId={selectedSessions[0]}
                    analysisType={activeTab}
                    allRouteData={currentRouteData}
                    sessionData={mergedSessionDetails}
                  />
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <FlaskIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 text-lg">Please select a probe session to begin analysis</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}