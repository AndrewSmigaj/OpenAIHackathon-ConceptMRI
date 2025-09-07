import { useState } from 'react'
import './App.css'
import type { ProbeResponse } from './types/api'
import { apiClient } from './api/client'

function App() {
  const [count, setCount] = useState(0)
  const [testResult, setTestResult] = useState<string>('')
  const [loading, setLoading] = useState(false)

  // Test that TypeScript types work
  const testType: ProbeResponse = {
    session_id: "test",
    total_pairs: 0,
    contexts: [],
    targets: [],
    categories: { contexts: {}, targets: {} }
  }

  const testApiConnection = async () => {
    setLoading(true)
    setTestResult('')
    
    try {
      const sessions = await apiClient.listSessions()
      setTestResult(`✅ API Connected! Found ${sessions.length} sessions.`)
    } catch (error) {
      setTestResult(`❌ API Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Concept MRI
          </h1>
          <p className="text-lg text-gray-600">
            Mixture of Experts Interpretability Research Platform
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-6">
            Frontend Setup Test
          </h2>
          
          <div className="space-y-4">
            <div className="flex items-center space-x-4">
              <span className="text-sm font-medium text-gray-700">React + TypeScript:</span>
              <span className="px-2 py-1 bg-green-100 text-green-800 text-sm rounded">✅ Ready</span>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-sm font-medium text-gray-700">Tailwind CSS:</span>
              <span className="px-2 py-1 bg-green-100 text-green-800 text-sm rounded">✅ Ready</span>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-sm font-medium text-gray-700">TypeScript Types:</span>
              <span className="px-2 py-1 bg-green-100 text-green-800 text-sm rounded">✅ {testType.session_id}</span>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-sm font-medium text-gray-700">Backend API:</span>
              <button
                onClick={testApiConnection}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Testing...' : 'Test Connection'}
              </button>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-sm font-medium text-gray-700">State Management:</span>
              <button 
                onClick={() => setCount(count + 1)}
                className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
              >
                Count: {count}
              </button>
            </div>
            
            {testResult && (
              <div className="mt-4 p-4 bg-gray-100 rounded text-sm font-mono">
                {testResult}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App