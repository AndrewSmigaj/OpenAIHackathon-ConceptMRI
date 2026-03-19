import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import type { SessionListItem } from '../types/api'
import { apiClient } from '../api/client'
import { FlaskIcon, ChartBarIcon } from '../components/icons/Icons'

export default function WorkspacePage() {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiClient.listSessions()
      setSessions(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions')
      console.error('Failed to load sessions:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleNewExperiment = () => {
    navigate('/experiment')
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const renderMainPanel = () => {
    return (
      <div className="bg-white rounded-xl shadow-md h-full">
        <div className="p-8 border-b border-gray-200">
          <h2 className="text-2xl font-semibold text-gray-900">Sessions</h2>
        </div>
        <div className="p-8">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
              ))}
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-600">{error}</p>
              <button
                onClick={loadSessions}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-12">
              <FlaskIcon className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-500 mb-4">No sessions yet</p>
              <p className="text-sm text-gray-400">Run a sentence experiment to create a session</p>
            </div>
          ) : (
            <div className="space-y-4">
              {sessions.map(session => (
                <div
                  key={session.session_id}
                  className="w-full text-left p-5 bg-gray-50 rounded-xl transition-colors border border-gray-200 shadow-sm cursor-default"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-semibold text-gray-900 mb-2">{session.session_name}</p>
                      <p className="text-sm text-gray-600">
                        {session.probe_count} probes • {session.state}
                        {session.target_word && ` • "${session.target_word}"`}
                      </p>
                      {session.labels && session.labels.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {session.labels.map(label => (
                            <span key={label} className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-800 capitalize">
                              {label}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <span className="text-sm text-gray-400 ml-4">
                      {formatDate(session.created_at)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
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
          <h1 className="text-2xl font-bold text-gray-900">Concept MRI</h1>
          <p className="text-sm text-gray-600">Mixture of Experts Interpretability Platform</p>
        </div>
      </div>

      <div className="flex h-[calc(100vh-88px)]">
        {/* Left Sidebar */}
        <div className="w-80 bg-white shadow-sm border-r flex flex-col">
          {/* Actions */}
          <div className="p-8 border-b">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Actions</h3>
            <div className="space-y-4">
              <button
                onClick={handleNewExperiment}
                className="w-full flex items-center p-4 bg-green-50 text-green-700 rounded-xl hover:bg-green-100 transition-colors shadow-sm"
              >
                <ChartBarIcon className="w-6 h-6 mr-4" />
                <div className="text-left">
                  <p className="font-medium text-sm">New Experiment</p>
                  <p className="text-xs text-green-600 mt-1">Analyze probe data</p>
                </div>
              </button>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="p-8 border-b">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Statistics</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Sessions</span>
                <span className="font-semibold text-lg text-gray-900">{sessions.length}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Total Probes</span>
                <span className="font-semibold text-lg text-gray-900">{sessions.reduce((sum, s) => sum + s.probe_count, 0)}</span>
              </div>
              {sessions.length > 0 && (
                <div className="pt-4 mt-4 border-t border-gray-200">
                  <p className="text-xs text-gray-500">
                    Last activity: {formatDate(sessions[0].created_at)}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Status */}
          <div className="p-8 mt-auto">
            <div className="flex items-center space-x-3 mb-3">
              <div className={`w-3 h-3 rounded-full ${loading ? 'bg-yellow-500' : 'bg-green-500'}`} />
              <span className="text-sm text-gray-600">
                Backend: {loading ? 'Loading...' : 'Connected'}
              </span>
            </div>
            <button
              onClick={loadSessions}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Refresh Sessions
            </button>
          </div>
        </div>

        {/* Main Panel */}
        <div className="flex-1 p-8">
          {renderMainPanel()}
        </div>
      </div>
    </div>
  )
}