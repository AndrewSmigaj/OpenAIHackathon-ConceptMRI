import { useState } from 'react'
import type { RouteAnalysisResponse, SessionDetailResponse } from '../../types/api'
import { apiClient } from '../../api/client'
import { FlaskIcon } from '../icons/Icons'

interface LLMAnalysisProps {
  sessionId: string
  selectedContext?: string
  analysisType: 'expert' | 'latent'
  allRouteData?: Record<string, RouteAnalysisResponse | null> | null
  sessionData?: SessionDetailResponse | null
}

export default function LLMAnalysisPanel({ sessionId, selectedContext, analysisType, allRouteData, sessionData }: LLMAnalysisProps) {
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
