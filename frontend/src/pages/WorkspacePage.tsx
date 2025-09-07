import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import type { SessionListItem } from '../types/api'
import { apiClient } from '../api/client'
import ActionCard from '../components/ActionCard'
import Modal from '../components/Modal'
import { FlaskIcon, ChartBarIcon, ClockIcon, ChartPieIcon } from '../components/icons/Icons'
import { MAX_RECENT_SESSIONS } from '../constants/workspace'

export default function WorkspacePage() {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showNewProbeDialog, setShowNewProbeDialog] = useState(false)
  const [showNoSessionsModal, setShowNoSessionsModal] = useState(false)

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
    if (sessions.length > 0) {
      // For now, navigate to the first session
      // TODO: Add session selector dialog
      navigate(`/experiment/${sessions[0].session_id}`)
    } else {
      setShowNoSessionsModal(true)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Concept MRI
            </h1>
            <p className="text-lg text-gray-600">
              Mixture of Experts Interpretability Platform
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Analyze how language models route information through expert networks
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Action Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <ActionCard
            title="Create New Probe"
            description="Capture MoE activations with WordNet integration for semantic analysis"
            icon={<FlaskIcon />}
            buttonText="New Probe"
            buttonColor="blue"
            onClick={() => setShowNewProbeDialog(true)}
          />

          <ActionCard
            title="New Experiment"
            description="Analyze captured probe data with expert highways and trajectory analysis"
            icon={<ChartBarIcon />}
            buttonText={sessions.length > 0 ? 'Select Session' : 'No Sessions Available'}
            buttonColor="green"
            onClick={handleNewExperiment}
            disabled={sessions.length === 0}
          />

          {/* Recent Sessions Card */}
          <div className="bg-white rounded-lg shadow-md">
            <div className="p-6">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 ml-3">Recent Sessions</h3>
              </div>
              
              {loading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
                  ))}
                </div>
              ) : error ? (
                <p className="text-red-600 text-sm">{error}</p>
              ) : sessions.length === 0 ? (
                <p className="text-gray-500 text-sm">No sessions yet. Create your first probe to get started!</p>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {sessions.slice(0, MAX_RECENT_SESSIONS).map(session => (
                    <button
                      key={session.session_id}
                      onClick={() => navigate(`/experiment/${session.session_id}`)}
                      className="w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium text-gray-900">{session.session_name}</p>
                          <p className="text-xs text-gray-500">
                            {session.probe_count} probes • {session.state}
                          </p>
                        </div>
                        <span className="text-xs text-gray-400">
                          {formatDate(session.created_at)}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Quick Stats Card */}
          <div className="bg-white rounded-lg shadow-md">
            <div className="p-6">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                          d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                          d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 ml-3">Statistics</h3>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-2xl font-bold text-gray-900">{sessions.length}</p>
                  <p className="text-sm text-gray-500">Total Sessions</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {sessions.reduce((sum, s) => sum + s.probe_count, 0)}
                  </p>
                  <p className="text-sm text-gray-500">Total Probes</p>
                </div>
                <div className="col-span-2 pt-2 border-t">
                  <p className="text-sm text-gray-500">
                    {sessions.length > 0 
                      ? `Last activity: ${formatDate(sessions[0].created_at)}`
                      : 'No activity yet'
                    }
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Status Bar */}
        <div className="bg-white rounded-lg shadow-md px-4 py-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${loading ? 'bg-yellow-500' : 'bg-green-500'}`} />
              <span className="text-sm text-gray-600">
                Backend: {loading ? 'Loading...' : 'Connected'}
              </span>
            </div>
            <button
              onClick={loadSessions}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      <Modal
        isOpen={showNewProbeDialog}
        onClose={() => setShowNewProbeDialog(false)}
        title="Create New Probe"
      >
        <p className="text-gray-600">
          NewProbeDialog component coming soon...
        </p>
      </Modal>

      <Modal
        isOpen={showNoSessionsModal}
        onClose={() => setShowNoSessionsModal(false)}
        title="No Sessions Available"
      >
        <p className="text-gray-600">
          No sessions available. Please create a probe first.
        </p>
      </Modal>
    </div>
  )
}