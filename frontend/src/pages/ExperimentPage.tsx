import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { SessionListItem, SessionDetailResponse } from '../types/api'
import { apiClient } from '../api/client'
import { FlaskIcon, ChartBarIcon } from '../components/icons/Icons'
import WordFilterPanel, { type FilterState } from '../components/WordFilterPanel'
import FilteredWordDisplay from '../components/FilteredWordDisplay'

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

function ColorControls({ colorScheme, onChange }: { colorScheme: string, onChange: (scheme: string) => void }) {
  return (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900">Color Controls</h4>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Color Scheme
        </label>
        <select
          value={colorScheme}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="semantic">Semantic Category</option>
          <option value="pos">POS Comparison</option>
          <option value="embedding">Embedding Distance</option>
          <option value="activation">Activation Magnitude</option>
        </select>
      </div>
    </div>
  )
}

function ExpertHighwaysTab({ 
  sessionId, 
  sessionData, 
  filterState 
}: { 
  sessionId: string
  sessionData: SessionDetailResponse | null
  filterState: FilterState
}) {
  const [colorScheme, setColorScheme] = useState('semantic')
  const [topRoutes, setTopRoutes] = useState(10)
  const [selectedCard, setSelectedCard] = useState<{ type: 'expert' | 'highway', data: any } | null>(null)

  const handleSankeyClick = (elementType: 'expert' | 'route', data: any) => {
    setSelectedCard({ 
      type: elementType === 'expert' ? 'expert' : 'highway', 
      data 
    })
  }

  return (
    <div className="flex space-x-8 h-full">
      {/* Left Controls */}
      <div className="w-64 space-y-8">
        <div className="bg-white rounded-xl shadow-md p-6">
          <ColorControls colorScheme={colorScheme} onChange={setColorScheme} />
        </div>
        
        <div className="bg-white rounded-xl shadow-md p-6">
          <h4 className="font-medium text-gray-900 mb-4">Visualization Config</h4>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Top Routes
            </label>
            <input
              type="number"
              value={topRoutes}
              onChange={(e) => setTopRoutes(parseInt(e.target.value))}
              min="5"
              max="50"
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Center Sankey */}
      <div className="flex-1">
        <div className="bg-white rounded-xl shadow-md p-8 h-full">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-xl font-semibold text-gray-900">Expert Routing Pathways</h3>
              <p className="text-sm text-gray-600 mt-1">Click experts or routes to see details</p>
            </div>
            <ChartBarIcon className="w-6 h-6 text-blue-600" />
          </div>
          
          {/* Interactive Sankey Placeholder */}
          <div className="h-full bg-gray-50 rounded-xl flex items-center justify-center border-2 border-dashed border-gray-300 cursor-pointer"
               onClick={() => handleSankeyClick('expert', { expertId: 'E14', population: 45, coverage: 23, specialization: 'Abstract concepts' })}>
            <div className="text-center">
              <ChartBarIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500 font-medium text-lg">Interactive Expert Routing Sankey</p>
              <p className="text-sm text-gray-400 mt-2">Click to test expert card</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right Context-Sensitive Card */}
      <div className="w-80">
        <ContextSensitiveCard 
          cardType={selectedCard?.type || 'expert'}
          selectedData={selectedCard?.data}
        />
      </div>
    </div>
  )
}

function LatentSpaceTab({ 
  sessionId, 
  sessionData, 
  filterState 
}: { 
  sessionId: string
  sessionData: SessionDetailResponse | null
  filterState: FilterState
}) {
  const [colorScheme, setColorScheme] = useState('semantic')
  const [clusterCount, setClusterCount] = useState(8)
  const [clusteringMethod, setClusteringMethod] = useState('kmeans')
  const [selectedCard, setSelectedCard] = useState<{ type: 'cluster' | 'route', data: any } | null>(null)

  const handleSankeyClick = (elementType: 'cluster' | 'trajectory', data: any) => {
    setSelectedCard({ 
      type: elementType === 'cluster' ? 'cluster' : 'route', 
      data 
    })
  }

  return (
    <div className="flex space-x-8 h-full">
      {/* Left Controls */}
      <div className="w-64 space-y-8">        
        <div className="bg-white rounded-xl shadow-md p-6">
          <h4 className="font-medium text-gray-900 mb-4">Clustering Controls</h4>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Clusters (K)
              </label>
              <input
                type="number"
                value={clusterCount}
                onChange={(e) => setClusterCount(parseInt(e.target.value))}
                min="2"
                max="20"
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Method
              </label>
              <select
                value={clusteringMethod}
                onChange={(e) => setClusteringMethod(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="kmeans">K-Means</option>
                <option value="hierarchical">Hierarchical</option>
                <option value="dbscan">DBSCAN</option>
              </select>
            </div>
            
            <button className="w-full px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors shadow-sm">
              Run Clustering
            </button>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-md p-6">
          <ColorControls colorScheme={colorScheme} onChange={setColorScheme} />
        </div>
      </div>

      {/* Center Visualizations */}
      <div className="flex-1">
        <div className="grid grid-rows-2 gap-6 h-full">
          {/* Trajectory Sankey */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Cluster Trajectory Routes</h3>
              <ChartBarIcon className="w-6 h-6 text-blue-600" />
            </div>
            
            <div className="h-full bg-gray-50 rounded-xl flex items-center justify-center border-2 border-dashed border-gray-300 cursor-pointer"
                 onClick={() => handleSankeyClick('cluster', { clusterId: 'C3', population: 67, coverage: 15, label: 'Abstract concepts' })}>
              <div className="text-center">
                <ChartBarIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500 font-medium">Interactive Trajectory Sankey</p>
                <p className="text-sm text-gray-400 mt-1">Click to test cluster card</p>
              </div>
            </div>
          </div>
          
          {/* PCA 3D */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">3D PCA Visualization</h3>
              <ChartBarIcon className="w-6 h-6 text-blue-600" />
            </div>
            
            <div className="h-full bg-gray-50 rounded-xl flex items-center justify-center border-2 border-dashed border-gray-300">
              <div className="text-center">
                <ChartBarIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500 font-medium">3D PCA Plot</p>
                <p className="text-sm text-gray-400 mt-1">With cluster coloring</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Context-Sensitive Card */}
      <div className="w-80">
        <ContextSensitiveCard 
          cardType={selectedCard?.type || 'cluster'}
          selectedData={selectedCard?.data}
        />
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
    targetCategories: new Set()
  })

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
        {/* Left Sidebar */}
        <div className="w-80 bg-white shadow-sm border-r flex flex-col">
          {/* Session Selector */}
          <div className="p-8 border-b">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Session</h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Probe Session
              </label>
              <select
                value={selectedSession}
                onChange={(e) => setSelectedSession(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select a completed session...</option>
                {sessions.filter(s => s.state === 'completed').map((session) => (
                  <option key={session.session_id} value={session.session_id}>
                    {session.session_name}
                  </option>
                ))}
              </select>
              {selectedSessionData && (
                <p className="text-sm text-gray-500 mt-2">
                  {selectedSessionData.probe_count} probes • {formatDate(selectedSessionData.created_at)}
                </p>
              )}
              
              <button
                onClick={() => {/* Session already loads via dropdown selection */}}
                disabled={!selectedSession}
                className="w-full mt-4 px-4 py-3 bg-green-600 text-white rounded-xl hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shadow-sm"
              >
                Create Experiment
              </button>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="p-8 border-b">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Analysis Type</h3>
            <div className="space-y-2">
              <button
                onClick={() => setActiveTab('expert')}
                className={`w-full flex items-center p-4 rounded-xl transition-colors shadow-sm ${
                  activeTab === 'expert'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                }`}
              >
                <ChartBarIcon className="w-5 h-5 mr-3" />
                <div className="text-left">
                  <p className="font-medium text-sm">Expert Highways</p>
                  <p className="text-xs opacity-75">MoE routing patterns</p>
                </div>
              </button>
              
              <button
                onClick={() => setActiveTab('latent')}
                className={`w-full flex items-center p-4 rounded-xl transition-colors shadow-sm ${
                  activeTab === 'latent'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                }`}
              >
                <ChartBarIcon className="w-5 h-5 mr-3" />
                <div className="text-left">
                  <p className="font-medium text-sm">Latent Space</p>
                  <p className="text-xs opacity-75">Cluster trajectories</p>
                </div>
              </button>
            </div>
          </div>

          {/* Word Filters */}
          {selectedSession && sessionDetails && (
            <div className="p-8 border-b">
              <WordFilterPanel
                sessionData={sessionDetails}
                selectedFilters={filterState}
                onFiltersChange={setFilterState}
                isLoading={!sessionDetails}
              />
            </div>
          )}

          {/* Filtered Words Display */}
          {selectedSession && sessionDetails && (
            <div className="p-8 border-b">
              <FilteredWordDisplay
                sessionData={sessionDetails}
                filterState={filterState}
                isLoading={!sessionDetails}
              />
            </div>
          )}

          {/* Quick Stats */}
          {selectedSessionData && (
            <div className="p-8 border-b">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">Session Info</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Probes</span>
                  <span className="font-semibold text-gray-900">{selectedSessionData.probe_count}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Status</span>
                  <span className="font-semibold text-gray-900">{selectedSessionData.state}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col">
          {selectedSession ? (
            <>
              <div className="flex-1 p-8">
                {activeTab === 'expert' && (
                  <ExpertHighwaysTab 
                    sessionId={selectedSession}
                    sessionData={sessionDetails}
                    filterState={filterState}
                  />
                )}
                {activeTab === 'latent' && (
                  <LatentSpaceTab 
                    sessionId={selectedSession}
                    sessionData={sessionDetails}
                    filterState={filterState}
                  />
                )}
              </div>
              
              {/* LLM Analysis Panel - Shared */}
              <div className="border-t bg-white p-8">
                <LLMAnalysisPanel sessionId={selectedSession} analysisType={activeTab} />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-gray-500">Please select a probe session to begin analysis.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}