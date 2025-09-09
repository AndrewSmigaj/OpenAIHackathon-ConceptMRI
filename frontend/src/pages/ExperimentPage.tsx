import { useState, useEffect } from 'react'
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
import { FlaskIcon, ChartBarIcon } from '../components/icons/Icons'
import WordFilterPanel, { type FilterState } from '../components/WordFilterPanel'
import FilteredWordDisplay from '../components/FilteredWordDisplay'
import SankeyChart from '../components/charts/SankeyChart'
import { getColorPreview, getAxisLabel, type ColorAxis } from '../utils/colorBlending'

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

interface LLMAnalysisProps {
  sessionId: string
  selectedContext?: string
  analysisType: 'expert' | 'latent'
}

interface ContextSensitiveCardProps {
  cardType: 'expert' | 'highway' | 'cluster' | 'route'
  selectedData: any
}

function LLMAnalysisPanel({ sessionId, selectedContext, analysisType }: LLMAnalysisProps) {
  const [apiKey, setApiKey] = useState('')
  const [analysis, setAnalysis] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const handleAnalyze = async () => {
    if (!apiKey.trim()) {
      alert('Please enter your OpenAI API key')
      return
    }
    
    setIsAnalyzing(true)
    try {
      // TODO: Call backend API to generate analysis
      await new Promise(resolve => setTimeout(resolve, 2000)) // Mock delay
      const contextInfo = selectedContext ? ` for ${selectedContext}` : ''
      setAnalysis(`Mock ${analysisType} pathway analysis${contextInfo} for session ${sessionId}...`)
    } catch (error) {
      console.error('Analysis failed:', error)
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-md p-8">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-gray-900">
          LLM Analysis - {analysisType === 'expert' ? 'Expert Pathways' : 'Cluster Routes'}
        </h3>
        <FlaskIcon className="w-6 h-6 text-blue-600" />
      </div>
      
      {!analysis ? (
        <div className="space-y-6">
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
            disabled={isAnalyzing || !apiKey.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            {isAnalyzing ? 'Analyzing...' : `Generate Analysis`}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-gray-50 rounded-xl p-6">
            <p className="text-gray-800">{analysis}</p>
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
  if (!selectedData) {
    return (
      <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-300 p-8 text-center">
        <div className="text-gray-500">
          <ChartBarIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <p className="font-medium">Click {cardType === 'expert' || cardType === 'highway' ? 'expert or route' : 'cluster or trajectory'}</p>
          <p className="text-sm mt-1">to see details here</p>
        </div>
      </div>
    )
  }

  const getCardTitle = () => {
    switch (cardType) {
      case 'expert': return `Expert ${selectedData.expertId || 'E?'}`
      case 'highway': return `Highway Route`
      case 'cluster': return `Cluster ${selectedData.clusterId || 'C?'}`
      case 'route': return `Trajectory Route`
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-md p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">{getCardTitle()}</h3>
        <ChartBarIcon className="w-5 h-5 text-blue-600" />
      </div>
      
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">Population</span>
          <span className="font-medium text-gray-900">{selectedData.population || 'Unknown'}</span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">Coverage</span>
          <span className="font-medium text-gray-900">{selectedData.coverage || '0'}%</span>
        </div>
        
        {cardType === 'expert' && (
          <div className="pt-4 border-t border-gray-200">
            <span className="text-sm text-gray-600">Specialization</span>
            <p className="text-gray-900 mt-1">{selectedData.specialization || 'Not analyzed'}</p>
          </div>
        )}
        
        {cardType === 'highway' && (
          <div className="pt-4 border-t border-gray-200">
            <span className="text-sm text-gray-600">Route Signature</span>
            <p className="text-gray-900 font-mono text-sm mt-1">{selectedData.signature || 'L?E?→L?E?'}</p>
          </div>
        )}
        
        {(cardType === 'cluster' || cardType === 'route') && (
          <div className="pt-4 border-t border-gray-200">
            <span className="text-sm text-gray-600">Label</span>
            <p className="text-gray-900 mt-1">{selectedData.label || 'Not labeled'}</p>
          </div>
        )}
        
        <div className="pt-4 border-t border-gray-200">
          <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
            Export Cohort
          </button>
        </div>
      </div>
    </div>
  )
}

interface ColorControlsProps {
  primaryAxis: ColorAxis
  secondaryAxis?: ColorAxis
  onPrimaryChange: (axis: ColorAxis) => void
  onSecondaryChange: (axis: ColorAxis | undefined) => void
}

function ColorControls({ primaryAxis, secondaryAxis, onPrimaryChange, onSecondaryChange }: ColorControlsProps) {
  const colorPreview = getColorPreview(primaryAxis, secondaryAxis)
  
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
                className="w-4 h-4 rounded border border-gray-300" 
                style={{ backgroundColor: color }}
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
  topRoutes,
  windowLayers,
  showAllRoutes
}: { 
  sessionId: string
  sessionData: SessionDetailResponse | null
  filterState: FilterState
  primaryAxis: ColorAxis
  secondaryAxis?: ColorAxis
  topRoutes: number
  windowLayers: number[]
  showAllRoutes: boolean
}) {
  const [selectedCard, setSelectedCard] = useState<{ type: 'expert' | 'highway', data: any } | null>(null)
  const [routeData, setRouteData] = useState<RouteAnalysisResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load route analysis data when dependencies change
  useEffect(() => {
    if (!sessionId || !sessionData) {
      setRouteData(null)
      return
    }

    const loadRoutes = async () => {
      try {
        setLoading(true)
        setError(null)
        
        const request: AnalyzeRoutesRequest = {
          session_id: sessionId,
          window_layers: windowLayers,
          filter_config: convertFilterState(filterState, sessionData),
          top_n_routes: showAllRoutes ? 1000 : topRoutes // Use large number for "all"
        }
        
        const response = await apiClient.analyzeRoutes(request)
        setRouteData(response)
      } catch (err) {
        console.error('Failed to load routes:', err)
        setError(err instanceof Error ? err.message : 'Failed to load routes')
        setRouteData(null)
      } finally {
        setLoading(false)
      }
    }

    loadRoutes()
  }, [sessionId, sessionData, filterState, windowLayers, topRoutes, showAllRoutes])

  const handleSankeyClick = (elementType: 'expert' | 'route', data: any) => {
    setSelectedCard({ 
      type: elementType === 'expert' ? 'expert' : 'highway', 
      data 
    })
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 h-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-semibold text-gray-900">Expert Routing Pathways</h3>
          <p className="text-sm text-gray-600 mt-1">Click experts or routes to see details</p>
        </div>
        <ChartBarIcon className="w-6 h-6 text-blue-600" />
      </div>
      
      {/* Route Analysis Visualization */}
      <div className="flex-1 bg-gray-50 rounded-lg min-h-[400px]">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading expert routes...</p>
              <p className="text-sm text-gray-500 mt-1">Analyzing layers {windowLayers.join('→')}</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <ChartBarIcon className="w-6 h-6 text-red-600" />
              </div>
              <p className="text-red-600 font-medium">Failed to load routes</p>
              <p className="text-sm text-gray-500 mt-1">{error}</p>
            </div>
          </div>
        ) : routeData ? (
          <div className="p-4 h-full">
            {/* Real Sankey Visualization */}
            <SankeyChart
              nodes={routeData.nodes}
              links={routeData.links}
              primaryAxis={primaryAxis}
              secondaryAxis={secondaryAxis}
              onNodeClick={(nodeId, nodeData) => {
                handleSankeyClick('expert', {
                  expertId: nodeData.expert_id,
                  population: nodeData.token_count,
                  coverage: Math.round((nodeData.token_count / routeData.statistics.total_probes) * 100),
                  specialization: `Layer ${nodeData.layer} specialist`,
                  categories: nodeData.categories
                })
              }}
              onLinkClick={(linkData) => {
                handleSankeyClick('route', {
                  signature: linkData.route_signature,
                  flow: linkData.value,
                  coverage: Math.round((linkData.value / routeData.statistics.total_probes) * 100)
                })
              }}
              width={700}
              height={400}
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <ChartBarIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500 font-medium text-lg">Select a completed session</p>
              <p className="text-sm text-gray-400 mt-2">Expert route analysis will appear here</p>
            </div>
          </div>
        )}
      </div>

      {/* Context-Sensitive Card integrated */}
      {selectedCard && (
        <div className="mt-6 pt-6 border-t border-gray-200">
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
  windowLayers,
  layerClusterCounts,
  clusteringMethod
}: { 
  sessionId: string
  sessionData: SessionDetailResponse | null
  filterState: FilterState
  primaryAxis: ColorAxis
  secondaryAxis?: ColorAxis
  windowLayers: number[]
  layerClusterCounts: {[key: number]: number}
  clusteringMethod: string
}) {
  const [selectedCard, setSelectedCard] = useState<{ type: 'cluster' | 'route', data: any } | null>(null)

  const handleVisualizationClick = (elementType: 'cluster' | 'trajectory', data: any) => {
    setSelectedCard({ 
      type: elementType === 'cluster' ? 'cluster' : 'route', 
      data 
    })
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 h-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-semibold text-gray-900">Latent Space Analysis</h3>
          <p className="text-sm text-gray-600 mt-1">Cluster trajectories and stepped PCA visualization</p>
        </div>
        <ChartBarIcon className="w-6 h-6 text-blue-600" />
      </div>
      
      <div className="flex flex-col h-full space-y-6">
        {/* Trajectory Sankey - Clusters and Paths */}
        <div className="bg-gray-50 rounded-lg p-4 flex-1">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-semibold text-gray-900">Cluster Trajectory Routes</h4>
            <ChartBarIcon className="w-5 h-5 text-blue-600" />
          </div>
          
          <div className="h-full bg-white rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300 cursor-pointer min-h-[200px]"
               onClick={() => handleVisualizationClick('cluster', { clusterId: 'C3', population: 67, coverage: 15, label: 'Abstract concepts' })}>
            <div className="text-center">
              <ChartBarIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500 font-medium">Cluster Trajectory Sankey</p>
              <p className="text-sm text-gray-400 mt-1">
                Layers {windowLayers.join('→')} • {clusteringMethod}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                K: {windowLayers.map(layer => `L${layer}=${layerClusterCounts[layer] || 6}`).join(', ')}
              </p>
            </div>
          </div>
        </div>
        
        {/* Stepped PCA Plot - All Three Layers */}
        <div className="bg-gray-50 rounded-lg p-4 flex-1">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-semibold text-gray-900">Stepped PCA Plot</h4>
            <ChartBarIcon className="w-5 h-5 text-blue-600" />
          </div>
          
          <div className="h-full bg-white rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300 min-h-[200px]">
            <div className="text-center">
              <ChartBarIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500 font-medium">Stepped PCA Visualization</p>
              <p className="text-sm text-gray-400 mt-1">Layers {windowLayers.join(' → ')}</p>
              <p className="text-xs text-gray-400 mt-1">
                {getAxisLabel(primaryAxis)}{secondaryAxis ? ` × ${getAxisLabel(secondaryAxis)}` : ''}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Context-Sensitive Card integrated */}
      {selectedCard && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <ContextSensitiveCard 
            cardType={selectedCard.type}
            selectedData={selectedCard.data}
          />
        </div>
      )}
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
  const [windowLayers, setWindowLayers] = useState<number[]>([0, 1])
  
  // Expert tab controls
  const [topRoutes, setTopRoutes] = useState(10)
  const [showAllRoutes, setShowAllRoutes] = useState(false)
  
  // Latent tab controls  
  const [layerClusterCounts, setLayerClusterCounts] = useState<{[key: number]: number}>({
    0: 6,
    1: 8, 
    2: 6
  })
  const [clusteringMethod, setClusteringMethod] = useState('kmeans')

  // Helper to update cluster counts when window changes
  const updateWindowLayers = (newWindow: number[]) => {
    setWindowLayers(newWindow)
    // Initialize cluster counts for new layers if not set
    const newCounts = { ...layerClusterCounts }
    newWindow.forEach(layer => {
      if (!(layer in newCounts)) {
        newCounts[layer] = 6 // default cluster count
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
        <div className="w-72 bg-white shadow-sm border-r flex flex-col">
          {/* Session Selector */}
          <div className="p-6 border-b">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Session</h3>
            <select
              value={selectedSession}
              onChange={(e) => setSelectedSession(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select a completed session...</option>
              {sessions.filter(s => s.state === 'completed').map((session) => (
                <option key={session.session_id} value={session.session_id}>
                  {session.session_name}
                </option>
              ))}
            </select>
            {selectedSessionData && (
              <p className="text-xs text-gray-500 mt-2">
                {selectedSessionData.probe_count} probes • {formatDate(selectedSessionData.created_at)}
              </p>
            )}
          </div>

          {/* Tab Navigation */}
          <div className="p-6 border-b">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Analysis Type</h3>
            <div className="space-y-2">
              <button
                onClick={() => setActiveTab('expert')}
                className={`w-full flex items-center p-3 rounded-lg transition-colors ${
                  activeTab === 'expert'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                }`}
              >
                <ChartBarIcon className="w-4 h-4 mr-2" />
                <div className="text-left">
                  <p className="font-medium text-sm">Expert Highways</p>
                  <p className="text-xs opacity-75">MoE routing patterns</p>
                </div>
              </button>
              
              <button
                onClick={() => setActiveTab('latent')}
                className={`w-full flex items-center p-3 rounded-lg transition-colors ${
                  activeTab === 'latent'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                }`}
              >
                <ChartBarIcon className="w-4 h-4 mr-2" />
                <div className="text-left">
                  <p className="font-medium text-sm">Latent Space</p>
                  <p className="text-xs opacity-75">Cluster trajectories</p>
                </div>
              </button>
            </div>
          </div>

          {/* Controls Section */}
          {selectedSession && (
            <div className="p-6 border-b flex-1">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Controls</h3>
              
              <div className="space-y-4">
                {/* Shared Controls */}
                <ColorControls 
                  primaryAxis={primaryAxis}
                  secondaryAxis={secondaryAxis}
                  onPrimaryChange={setPrimaryAxis}
                  onSecondaryChange={setSecondaryAxis}
                />

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
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">Per-Layer Clustering</h4>
                      {windowLayers.map((layer) => (
                        <div key={layer} className="mb-3">
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Layer {layer} Clusters (K)
                          </label>
                          <input
                            type="number"
                            value={layerClusterCounts[layer] || 6}
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
                      ))}
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
                    
                    <button className="w-full px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                      Run Clustering
                    </button>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Session Stats */}
          {selectedSessionData && (
            <div className="p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Session Info</h3>
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
              <div className="w-96 bg-gray-50 border-r p-6 space-y-6">
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
                <div className="flex-1 p-6">
                  {activeTab === 'expert' && (
                    <ExpertHighwaysTab 
                      sessionId={selectedSession}
                      sessionData={sessionDetails}
                      filterState={filterState}
                      primaryAxis={primaryAxis}
                      secondaryAxis={secondaryAxis}
                      topRoutes={topRoutes}
                      windowLayers={windowLayers}
                      showAllRoutes={showAllRoutes}
                    />
                  )}
                  {activeTab === 'latent' && (
                    <LatentSpaceTab 
                      sessionId={selectedSession}
                      sessionData={sessionDetails}
                      filterState={filterState}
                      primaryAxis={primaryAxis}
                      secondaryAxis={secondaryAxis}
                      windowLayers={windowLayers}
                      layerClusterCounts={layerClusterCounts}
                      clusteringMethod={clusteringMethod}
                    />
                  )}
                </div>
                
                {/* LLM Analysis Panel - Below Visualization */}
                <div className="border-t bg-white p-6">
                  <LLMAnalysisPanel sessionId={selectedSession} analysisType={activeTab} />
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