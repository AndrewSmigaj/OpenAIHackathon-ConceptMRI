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
import SteppedPCAPlot from '../components/charts/SteppedPCAPlot'
import { getColorPreview, getAxisLabel, type ColorAxis, type GradientScheme, GRADIENT_SCHEMES } from '../utils/colorBlending'
import { LAYER_RANGES } from '../constants/layerRanges'

/**
 * Sample words randomly from a category
 */
function sampleWordsFromCategory(words: string[], maxCount: number): string[] {
  if (words.length <= maxCount) return [...words];
  
  // Fisher-Yates shuffle and take first N
  const shuffled = [...words];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled.slice(0, maxCount);
}

/**
 * Apply balanced sampling to get word lists per category
 */
function applyBalancedSampling(
  sessionData: SessionDetailResponse, 
  filterState: FilterState
): { contextWords?: string[], targetWords?: string[] } {
  console.log('🎯 applyBalancedSampling called:', {
    balanceCategories: filterState.balanceCategories,
    maxWordsPerCategory: filterState.maxWordsPerCategory,
    selectedContextCategories: Array.from(filterState.contextCategories),
    selectedTargetCategories: Array.from(filterState.targetCategories)
  });

  if (!filterState.balanceCategories || !sessionData) {
    console.log('🎯 Not sampling - balanceCategories disabled or no sessionData');
    return {};
  }

  const selectedContextCategories = Array.from(filterState.contextCategories);
  const selectedTargetCategories = Array.from(filterState.targetCategories);
  
  // Sample context words
  let contextWords: string[] = [];
  if (selectedContextCategories.length > 0) {
    selectedContextCategories.forEach(category => {
      const wordsInCategory = Object.keys(sessionData.categories.contexts)
        .filter(word => sessionData.categories.contexts[word].includes(category));
      console.log(`🎯 Context category "${category}": ${wordsInCategory.length} words available`);
      const sampledWords = sampleWordsFromCategory(wordsInCategory, filterState.maxWordsPerCategory);
      console.log(`🎯 Context category "${category}": sampled ${sampledWords.length} words`);
      contextWords.push(...sampledWords);
    });
  }
  
  // Sample target words
  let targetWords: string[] = [];
  if (selectedTargetCategories.length > 0) {
    selectedTargetCategories.forEach(category => {
      const wordsInCategory = Object.keys(sessionData.categories.targets)
        .filter(word => sessionData.categories.targets[word].includes(category));
      console.log(`🎯 Target category "${category}": ${wordsInCategory.length} words available`);
      const sampledWords = sampleWordsFromCategory(wordsInCategory, filterState.maxWordsPerCategory);
      console.log(`🎯 Target category "${category}": sampled ${sampledWords.length} words`);
      targetWords.push(...sampledWords);
    });
  }

  const result = {
    contextWords: contextWords.length > 0 ? contextWords : undefined,
    targetWords: targetWords.length > 0 ? targetWords : undefined
  };
  
  console.log('🎯 applyBalancedSampling result:', {
    contextWordsCount: result.contextWords?.length || 0,
    targetWordsCount: result.targetWords?.length || 0
  });

  return result;
}

/**
 * Convert frontend FilterState to backend filter_config format.
 * Empty sets mean "include all" (no filtering), so we return undefined.
 * Non-empty sets mean "include words with ANY matching category".
 */
function convertFilterState(
  filterState: FilterState, 
  sessionData?: SessionDetailResponse
): AnalyzeRoutesRequest['filter_config'] {
  const filterConfig: NonNullable<AnalyzeRoutesRequest['filter_config']> = {};
  
  if (filterState.contextCategories.size > 0) {
    filterConfig.context_categories = Array.from(filterState.contextCategories);
  }
  if (filterState.targetCategories.size > 0) {
    filterConfig.target_categories = Array.from(filterState.targetCategories);
  }

  // Apply balanced sampling if enabled
  if (filterState.balanceCategories && sessionData) {
    console.log('🎯 convertFilterState: calling applyBalancedSampling');
    const sampledWords = applyBalancedSampling(sessionData, filterState);
    if (sampledWords.contextWords) {
      filterConfig.context_words = sampledWords.contextWords;
      console.log(`🎯 convertFilterState: added ${sampledWords.contextWords.length} context words`);
    }
    if (sampledWords.targetWords) {
      filterConfig.target_words = sampledWords.targetWords;
      console.log(`🎯 convertFilterState: added ${sampledWords.targetWords.length} target words`);
    }
    filterConfig.max_per_category = filterState.maxWordsPerCategory;
  }

  console.log('🎯 convertFilterState final result:', filterConfig);

  // Return undefined if no filters applied (empty object means include all)
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

function ContextSensitiveCard({ cardType, selectedData }: ContextSensitiveCardProps) {
  const [activeTab, setActiveTab] = useState<'details' | 'examples'>('details')
  const [isGeneratingLabel, setIsGeneratingLabel] = useState(false)
  const [customLabel, setCustomLabel] = useState<string>('')
  
  // Type-safe detection of rich data from Sankey clicks
  const hasRichData = Boolean(selectedData?._fullData)
  const isExpert = cardType === 'expert' || cardType === 'highway'
  const isRoute = cardType === 'route' || cardType === 'highway'

  // Safely extract category distribution for experts
  const categoryDistribution = hasRichData && isExpert && selectedData?.category_distribution 
    ? selectedData.category_distribution as Record<string, number>
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
                      {/* Category Distribution */}
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3 text-sm">Category Distribution</h4>
                        <div className="space-y-3 max-h-60 overflow-y-auto">
                          {(() => {
                            // Define category axes
                            const categoryAxes = {
                              'Grammatical': ['nouns', 'verbs'],
                              'Sentiment': ['positive', 'negative', 'neutral'],
                              'Abstraction': ['concrete', 'abstract'],
                              'Conceptual': ['temporal', 'cognitive']
                            }
                            
                            // Calculate axis-based percentages from existing category_distribution
                            const axisDistributions = []
                            
                            for (const [axisName, axisCategories] of Object.entries(categoryAxes)) {
                              const axisStats = analysis.categoryStats.filter(s => axisCategories.includes(s.category))
                              if (axisStats.length > 0) {
                                // Calculate total for this axis
                                const axisTotal = axisStats.reduce((sum, stat) => sum + stat.count, 0)
                                // Recalculate percentages within this axis
                                const axisPercents = axisStats.map(stat => ({
                                  ...stat,
                                  percentage: axisTotal > 0 ? (stat.count / axisTotal) * 100 : 0
                                }))
                                axisDistributions.push({ name: axisName, stats: axisPercents })
                              }
                            }
                            
                            // Also check for any old-style categories
                            const posAxis = analysis.categoryStats.filter(s => ['content', 'function'].includes(s.category))
                            const complexityAxis = analysis.categoryStats.filter(s => ['simple', 'complex'].includes(s.category))
                            
                            // Add old-style categories if they exist
                            if (posAxis.length > 0) axisDistributions.push({ name: 'POS', stats: posAxis })
                            if (complexityAxis.length > 0) axisDistributions.push({ name: 'Complexity', stats: complexityAxis })
                            
                            return axisDistributions.map(axis => (
                              <div key={axis.name} className="border border-gray-200 rounded-lg p-3">
                                <h5 className="font-medium text-gray-800 mb-2 text-xs">{axis.name}</h5>
                                <div className="space-y-2">
                                  {axis.stats.map(stat => (
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
                            ))
                          })()}
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

            {activeTab === 'examples' && (
              <div className="space-y-4">
                <h4 className="font-medium text-gray-900">Examples</h4>
                {isExpert && Array.isArray(selectedData.context_target_pairs) && selectedData.context_target_pairs.length > 0 ? (
                  <div className="space-y-3">
                    {selectedData.context_target_pairs.map((pair: any, index: number) => (
                      <div key={index} className="bg-gray-50 p-3 rounded-lg">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className="text-sm font-medium text-gray-900">"{pair.context || 'N/A'}"</span>
                          <span className="text-gray-400">→</span>
                          <span className="text-xs text-gray-500">
                            {typeof pair.target_count === 'number' ? pair.target_count : 0} targets
                          </span>
                        </div>
                        {Array.isArray(pair.targets) ? (
                          <div className="flex flex-wrap gap-2">
                            {pair.targets.slice(0, 8).map((target: string) => (
                              <span key={target} className="inline-block px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                                {target}
                              </span>
                            ))}
                            {pair.targets.length > 8 && (
                              <span className="text-xs text-gray-500">+{pair.targets.length - 8} more</span>
                            )}
                          </div>
                        ) : (
                          <div className="text-sm text-gray-700">
                            {typeof pair.targets === 'string' ? pair.targets.split(',').join(', ') : String(pair.targets || '')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : isRoute && Array.isArray(selectedData.example_tokens) && selectedData.example_tokens.length > 0 ? (
                  <div className="space-y-3">
                    {selectedData.example_tokens.slice(0, 10).map((token: any, index: number) => (
                      <div key={index} className="bg-gray-50 p-3 rounded-lg">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-medium text-gray-900">"{token.context || 'N/A'}"</span>
                          <span className="text-gray-400">→</span>
                          <span className="text-sm font-medium text-gray-900">"{token.target || 'N/A'}"</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No examples available</p>
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

interface ColorControlsProps {
  primaryAxis: ColorAxis
  secondaryAxis?: ColorAxis
  primaryGradient: GradientScheme
  secondaryGradient: GradientScheme
  onPrimaryChange: (axis: ColorAxis) => void
  onSecondaryChange: (axis: ColorAxis | undefined) => void
  onPrimaryGradientChange: (gradient: GradientScheme) => void
  onSecondaryGradientChange: (gradient: GradientScheme) => void
}

function ColorControls({ 
  primaryAxis, 
  secondaryAxis, 
  primaryGradient, 
  secondaryGradient, 
  onPrimaryChange, 
  onSecondaryChange, 
  onPrimaryGradientChange, 
  onSecondaryGradientChange 
}: ColorControlsProps) {
  // Map ColorAxis to category pairs for the new getColorPreview function
  const AXIS_CATEGORY_MAP: Record<ColorAxis, { neg: string; pos: string }> = {
    sentiment: { neg: 'negative', pos: 'positive' },
    concreteness: { neg: 'abstract', pos: 'concrete' },
    pos: { neg: 'nouns', pos: 'verbs' },
    'action-content': { neg: 'action', pos: 'content' }
  }
  
  const primary = AXIS_CATEGORY_MAP[primaryAxis]
  const secondary = secondaryAxis ? AXIS_CATEGORY_MAP[secondaryAxis] : undefined
  
  const colorPreview = getColorPreview(
    primary.neg, 
    primary.pos, 
    secondary?.neg, 
    secondary?.pos,
    primaryGradient,
    secondaryGradient
  )
  
  return (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900">Color Controls</h4>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Primary Axis
        </label>
        <select
          value={primaryAxis}
          onChange={(e) => onPrimaryChange(e.target.value as ColorAxis)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="sentiment">Sentiment</option>
          <option value="concreteness">Concreteness</option>
          <option value="pos">Part of Speech</option>
          <option value="temporal">Temporal vs Cognitive</option>
        </select>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Secondary Axis (Optional)
        </label>
        <select
          value={secondaryAxis || ''}
          onChange={(e) => onSecondaryChange(e.target.value ? e.target.value as ColorAxis : undefined)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">None (Pure Colors)</option>
          <option value="sentiment" disabled={primaryAxis === 'sentiment'}>Sentiment</option>
          <option value="concreteness" disabled={primaryAxis === 'concreteness'}>Concreteness</option>
          <option value="pos" disabled={primaryAxis === 'pos'}>Part of Speech</option>
          <option value="temporal" disabled={primaryAxis === 'temporal'}>Temporal vs Cognitive</option>
        </select>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Primary Gradient
        </label>
        <select
          value={primaryGradient}
          onChange={(e) => onPrimaryGradientChange(e.target.value as GradientScheme)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          {Object.entries(GRADIENT_SCHEMES).map(([key, scheme]) => (
            <option key={key} value={key}>{scheme.name}</option>
          ))}
        </select>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Secondary Gradient
        </label>
        <select
          value={secondaryGradient}
          onChange={(e) => onSecondaryGradientChange(e.target.value as GradientScheme)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          {Object.entries(GRADIENT_SCHEMES).map(([key, scheme]) => (
            <option key={key} value={key}>{scheme.name}</option>
          ))}
        </select>
      </div>
      
      {/* Color Preview */}
      <div className="pt-2 border-t border-gray-200">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Color Preview
        </label>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {Object.entries(colorPreview).slice(0, 8).map(([label, color]) => (
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
    </div>
  )
}

function ExpertHighwaysTab({ 
  sessionId, 
  sessionData, 
  filterState,
  primaryAxis,
  secondaryAxis,
  primaryGradient,
  secondaryGradient,
  topRoutes,
  selectedRange,
  onRangeChange,
  showAllRoutes,
  onRouteDataLoaded
}: { 
  sessionId: string
  sessionData: SessionDetailResponse | null
  filterState: FilterState
  primaryAxis: ColorAxis
  secondaryAxis?: ColorAxis
  primaryGradient: GradientScheme
  secondaryGradient: GradientScheme
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
          sessionId={sessionId}
          sessionData={sessionData}
          filterState={filterState}
          primaryAxis={primaryAxis}
          secondaryAxis={secondaryAxis}
          primaryGradient={primaryGradient}
          secondaryGradient={secondaryGradient}
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
          />
        </div>
      )}
    </div>
  )
}

function LatentSpaceTab({ 
  sessionId, 
  sessionData, 
  filterState,
  primaryAxis,
  secondaryAxis,
  primaryGradient,
  secondaryGradient,
  selectedRange,
  onRangeChange,
  layerClusterCounts,
  clusteringMethod,
  pcaDimensions,
  useAllLayersSameClusters,
  setUseAllLayersSameClusters,
  globalClusterCount,
  setGlobalClusterCount
}: { 
  sessionId: string
  sessionData: SessionDetailResponse | null
  filterState: FilterState
  primaryAxis: ColorAxis
  secondaryAxis?: ColorAxis
  primaryGradient: GradientScheme
  secondaryGradient: GradientScheme
  selectedRange: string
  onRangeChange: (range: string) => void
  layerClusterCounts: {[key: number]: number}
  clusteringMethod: string
  pcaDimensions: number
  useAllLayersSameClusters: boolean
  setUseAllLayersSameClusters: (value: boolean) => void
  globalClusterCount: number
  setGlobalClusterCount: (value: number) => void
}) {
  const [selectedCard, setSelectedCard] = useState<{ type: 'cluster' | 'route', data: any } | null>(null)
  const [runAnalysis, setRunAnalysis] = useState<(() => void) | null>(null)
  const [runPCAAnalysis, setRunPCAAnalysis] = useState<(() => void) | null>(null)

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

  const handlePCAAnalysisReady = useCallback((analysisFunction: () => void) => {
    setRunPCAAnalysis(() => analysisFunction)
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
      pca_dimensions: pcaDimensions,
      clustering_method: clusteringMethod,
      layer_cluster_counts: effectiveLayerClusterCounts
    };
  }, [pcaDimensions, clusteringMethod, layerClusterCounts, useAllLayersSameClusters, globalClusterCount, memoizedLayers])

  return (
    <div className="bg-white rounded-xl shadow-sm p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Latent Space Analysis</h3>
          <p className="text-xs text-gray-600 mt-1">Cluster trajectories and stepped PCA visualization</p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => {
              runAnalysis?.()
              runPCAAnalysis?.()
            }}
            disabled={!runAnalysis || !runPCAAnalysis}
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
            sessionId={sessionId}
            sessionData={sessionData}
            filterState={filterState}
            primaryAxis={primaryAxis}
            secondaryAxis={secondaryAxis}
            primaryGradient={primaryGradient}
            secondaryGradient={secondaryGradient}
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
        
        {/* Stepped PCA Plot - All Three Layers */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-4">
          <SteppedPCAPlot
            sessionId={sessionId}
            layers={memoizedLayers}
            primaryAxis={primaryAxis}
            secondaryAxis={secondaryAxis}
            primaryGradient={primaryGradient}
            secondaryGradient={secondaryGradient}
            sessionData={sessionData}
            filterConfig={convertFilterState(filterState, sessionData)}
            height={400}
            maxTrajectories={100}
            manualTrigger={true}
            onAnalysisReady={handlePCAAnalysisReady}
          />
        </div>

        {/* Context-Sensitive Card integrated */}
        {selectedCard && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <ContextSensitiveCard 
              cardType={selectedCard.type}
              selectedData={selectedCard.data}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default function ExperimentPage() {
  const { id } = useParams<{ id: string }>()
  const [selectedSession, setSelectedSession] = useState<string>('')
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [sessionDetails, setSessionDetails] = useState<SessionDetailResponse | null>(null)
  const [activeTab, setActiveTab] = useState<'expert' | 'latent'>('expert')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterState, setFilterState] = useState<FilterState>({
    contextCategories: new Set(),
    targetCategories: new Set(),
    balanceCategories: false,
    maxWordsPerCategory: 100
  })

  // Shared controls
  const [primaryAxis, setPrimaryAxis] = useState<ColorAxis>('sentiment')
  const [secondaryAxis, setSecondaryAxis] = useState<ColorAxis | undefined>('concreteness')
  const [primaryGradient, setPrimaryGradient] = useState<GradientScheme>('red-blue')
  const [secondaryGradient, setSecondaryGradient] = useState<GradientScheme>('yellow-cyan')
  const [windowLayers, setWindowLayers] = useState<number[]>([0, 1])
  const [selectedRange, setSelectedRange] = useState<string>('range1')
  
  // Expert tab controls
  const [topRoutes, setTopRoutes] = useState(10)
  const [showAllRoutes, setShowAllRoutes] = useState(false)
  
  // Latent tab controls  
  const [layerClusterCounts, setLayerClusterCounts] = useState<{[key: number]: number}>({})
  const [clusteringMethod, setClusteringMethod] = useState('kmeans')
  const [pcaDimensions, setPcaDimensions] = useState(3)
  const [customDimensions, setCustomDimensions] = useState(15)
  const [useCustomDimensions, setUseCustomDimensions] = useState(false)
  
  // Cluster configuration mode
  const [useAllLayersSameClusters, setUseAllLayersSameClusters] = useState(true)  // Default to "same for all"
  const [globalClusterCount, setGlobalClusterCount] = useState(4)  // Default to 4 clusters

  // LLM Insights state
  const [currentRouteData, setCurrentRouteData] = useState<Record<string, RouteAnalysisResponse | null> | null>(null)

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
    if (selectedSession) {
      loadSessionDetails()
    }
  }, [selectedSession])

  const loadSessionDetails = async () => {
    if (!selectedSession) return
    
    // Check if session is ready for analysis
    const sessionInfo = sessions.find(s => s.session_id === selectedSession)
    if (!sessionInfo || sessionInfo.state !== 'completed') {
      setSessionDetails(null)
      return
    }
    
    try {
      const details = await apiClient.getSessionDetails(selectedSession)
      setSessionDetails(details)
    } catch (err) {
      console.error('Failed to load session details:', err)
      setSessionDetails(null)
      // Could add user notification here if needed
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
        setSelectedSession(id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions')
      console.error('Failed to load sessions:', err)
    } finally {
      setLoading(false)
    }
  }

  const selectedSessionData = sessions.find(s => s.session_id === selectedSession)

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
          {/* Session Selector */}
          <div className="p-2 border-b">
            <select
              value={selectedSession}
              onChange={(e) => setSelectedSession(e.target.value)}
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">Select session...</option>
              {sessions.filter(s => s.state === 'completed').map((session) => (
                <option key={session.session_id} value={session.session_id}>
                  {session.session_name}
                </option>
              ))}
            </select>
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
          {selectedSession && (
            <div className="p-3 border-b flex-1">
              <h3 className="text-xs font-semibold text-gray-900 mb-2">Controls</h3>
              
              <div className="space-y-4">
                {/* Shared Controls */}
                <div className="border-t border-gray-200 pt-3 mt-3">
                  <ColorControls 
                  primaryAxis={primaryAxis}
                  secondaryAxis={secondaryAxis}
                  primaryGradient={primaryGradient}
                  secondaryGradient={secondaryGradient}
                  onPrimaryChange={setPrimaryAxis}
                  onSecondaryChange={setSecondaryAxis}
                  onPrimaryGradientChange={setPrimaryGradient}
                  onSecondaryGradientChange={setSecondaryGradient}
                  />
                </div>

                {/* Balanced Sampling Controls */}
                <div className="pt-4 border-t border-gray-200">
                  <h4 className="font-medium text-gray-900 mb-3">Balanced Sampling</h4>
                  
                  <div className="space-y-3">
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={filterState.balanceCategories}
                        onChange={(e) => setFilterState(prev => ({
                          ...prev,
                          balanceCategories: e.target.checked
                        }))}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium text-gray-700">Balance Categories</span>
                    </label>
                    
                    {filterState.balanceCategories && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Max Words per Category
                        </label>
                        <input
                          type="number"
                          value={filterState.maxWordsPerCategory}
                          onChange={(e) => setFilterState(prev => ({
                            ...prev,
                            maxWordsPerCategory: parseInt(e.target.value) || 100
                          }))}
                          min="10"
                          max="1000"
                          step="10"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Randomly sample up to this many words per category
                        </p>
                      </div>
                    )}
                  </div>
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
                    <div className="border-t border-gray-200 pt-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">PCA Dimensions for Clustering</h4>
                      <div className="mb-4">
                        <div className="space-y-2">
                          {[2, 3, 5, 10].map(dim => (
                            <label key={dim} className="flex items-center">
                              <input
                                type="radio"
                                name="pcaDimensions"
                                checked={pcaDimensions === dim && !useCustomDimensions}
                                onChange={() => {
                                  setPcaDimensions(dim)
                                  setUseCustomDimensions(false)
                                }}
                                className="mr-2"
                              />
                              <span className="text-sm">
                                {dim}D (PC1-{dim}) - {
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
                              name="pcaDimensions"
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
          {selectedSession ? (
            <>
              {/* Middle Column - Word Lists */}
              <div className="bg-gray-50 border-r p-4 space-y-4 word-panel-narrow">
                {sessionDetails && (
                  <>
                    <WordFilterPanel
                      sessionData={sessionDetails}
                      selectedFilters={filterState}
                      onFiltersChange={setFilterState}
                      isLoading={!sessionDetails}
                    />
                    
                    <FilteredWordDisplay
                      sessionData={sessionDetails}
                      filterState={filterState}
                      isLoading={!sessionDetails}
                    />
                  </>
                )}
              </div>

              {/* Right Column - Visualization + LLM Analysis */}
              <div className="flex-1 flex flex-col">
                <div className="flex-1 p-4">
                  {activeTab === 'expert' && (
                    <ExpertHighwaysTab 
                      sessionId={selectedSession}
                      sessionData={sessionDetails}
                      filterState={filterState}
                      primaryAxis={primaryAxis}
                      secondaryAxis={secondaryAxis}
                      primaryGradient={primaryGradient}
                      secondaryGradient={secondaryGradient}
                      topRoutes={topRoutes}
                      selectedRange={selectedRange}
                      onRangeChange={setSelectedRange}
                      showAllRoutes={showAllRoutes}
                      onRouteDataLoaded={setCurrentRouteData}
                    />
                  )}
                  {activeTab === 'latent' && (
                    <LatentSpaceTab 
                      sessionId={selectedSession}
                      sessionData={sessionDetails}
                      filterState={filterState}
                      primaryAxis={primaryAxis}
                      secondaryAxis={secondaryAxis}
                      primaryGradient={primaryGradient}
                      secondaryGradient={secondaryGradient}
                      selectedRange={selectedRange}
                      onRangeChange={setSelectedRange}
                      layerClusterCounts={layerClusterCounts}
                      clusteringMethod={clusteringMethod}
                      pcaDimensions={useCustomDimensions ? customDimensions : pcaDimensions}
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
                    sessionId={selectedSession} 
                    analysisType={activeTab}
                    allRouteData={currentRouteData}
                    sessionData={sessionDetails}
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