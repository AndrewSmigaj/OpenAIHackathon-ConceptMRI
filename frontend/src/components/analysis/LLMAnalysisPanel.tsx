import { useState, useEffect, useRef } from 'react'
import type {
  RouteAnalysisResponse,
  SessionDetailResponse,
  ScaffoldTemplate,
  ScaffoldStepRequest,
} from '../../types/api'
import { apiClient } from '../../api/client'

import ReactMarkdown from 'react-markdown'

interface ScaffoldStepState {
  template: ScaffoldTemplate
  selected: boolean
  status: 'idle' | 'running' | 'done' | 'error'
  editedPrompt?: string
  output?: string
  elementLabels?: Record<string, string>
  error?: string
}

interface RangeScaffoldState {
  steps: ScaffoldStepState[]
  outputs: string[] // accumulated narrative outputs for "previous_outputs"
}

interface LLMAnalysisPanelProps {
  sessionId: string
  expertRouteData?: Record<string, RouteAnalysisResponse | null> | null
  clusterRouteData?: Record<string, RouteAnalysisResponse | null> | null
  selectedRange: string
  onElementDescriptionsLoaded: (descs: Record<string, string>) => void
}

export default function LLMAnalysisPanel({
  sessionId,
  expertRouteData,
  clusterRouteData,
  selectedRange,
  onElementDescriptionsLoaded,
}: LLMAnalysisPanelProps) {
  const [apiKey, setApiKey] = useState('')
  const [templates, setTemplates] = useState<ScaffoldTemplate[]>([])
  const [rangeStates, setRangeStates] = useState<Record<string, RangeScaffoldState>>({})
  const [expandedStep, setExpandedStep] = useState<string | null>(null)
  const [viewingOutput, setViewingOutput] = useState<string | null>(null)
  const [loadingTemplates, setLoadingTemplates] = useState(true)

  // Load scaffold templates on mount
  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const loaded = await apiClient.getScaffoldTemplates()
        setTemplates(loaded)
      } catch (err) {
        console.error('Failed to load scaffold templates:', err)
      } finally {
        setLoadingTemplates(false)
      }
    }
    loadTemplates()
  }, [])

  // Get or initialize state for current range
  const currentState: RangeScaffoldState = rangeStates[selectedRange] || {
    steps: templates.map(t => ({
      template: t,
      selected: false,
      status: 'idle' as const,
    })),
    outputs: [],
  }

  // Sync steps when templates load or range changes
  useEffect(() => {
    if (templates.length === 0) return
    setRangeStates(prev => {
      const existing = prev[selectedRange]
      if (existing && existing.steps.length === templates.length) return prev
      return {
        ...prev,
        [selectedRange]: {
          steps: templates.map(t => {
            const existingStep = existing?.steps.find(s => s.template.id === t.id)
            return existingStep || {
              template: t,
              selected: false,
              status: 'idle' as const,
            }
          }),
          outputs: existing?.outputs || [],
        }
      }
    })
  }, [templates, selectedRange])

  const updateStep = (stepId: string, updates: Partial<ScaffoldStepState>) => {
    setRangeStates(prev => {
      const current = prev[selectedRange]
      if (!current) return prev
      return {
        ...prev,
        [selectedRange]: {
          ...current,
          steps: current.steps.map(s =>
            s.template.id === stepId ? { ...s, ...updates } : s
          ),
        }
      }
    })
  }

  const runStep = async (step: ScaffoldStepState) => {
    if (!apiKey.trim()) {
      alert('Please enter your API key')
      return
    }

    const prompt = step.editedPrompt || step.template.prompt
    updateStep(step.template.id, { status: 'running', error: undefined })

    try {
      // Build windows data from route data
      const expertWindows = step.template.data_sources.includes('expert_routes') && expertRouteData
        ? Object.values(expertRouteData).filter(d => d !== null)
        : null
      const clusterWindows = step.template.data_sources.includes('cluster_routes') && clusterRouteData
        ? Object.values(clusterRouteData).filter(d => d !== null)
        : null

      const currentOutputs = rangeStates[selectedRange]?.outputs || []

      const request: ScaffoldStepRequest = {
        session_id: sessionId,
        step_id: step.template.id,
        prompt,
        data_sources: step.template.data_sources,
        output_type: step.template.output_type,
        expert_windows: expertWindows,
        cluster_windows: clusterWindows,
        previous_outputs: step.template.data_sources.includes('previous_outputs') ? currentOutputs : null,
        api_key: apiKey,
        provider: 'openai',
      }

      const response = await apiClient.runScaffoldStep(request)

      if (step.template.output_type === 'element_labels' && response.element_labels) {
        updateStep(step.template.id, {
          status: 'done',
          elementLabels: response.element_labels,
          output: `Generated ${Object.keys(response.element_labels).length} element descriptions`,
        })
        onElementDescriptionsLoaded(response.element_labels)
      } else {
        updateStep(step.template.id, {
          status: 'done',
          output: response.narrative || '',
        })
        // Add to accumulated outputs for subsequent steps
        if (response.narrative) {
          setRangeStates(prev => {
            const current = prev[selectedRange]
            if (!current) return prev
            return {
              ...prev,
              [selectedRange]: {
                ...current,
                outputs: [...current.outputs, response.narrative!],
              }
            }
          })
        }
      }

      // Auto-select this step's output for viewing
      setViewingOutput(step.template.id)

    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error'
      updateStep(step.template.id, { status: 'error', error: errorMsg })
    }
  }

  const runSelected = async () => {
    const selectedSteps = currentState.steps.filter(s => s.selected)
    if (selectedSteps.length === 0) return

    for (const step of selectedSteps) {
      await runStep(step)
    }
  }

  const toggleStepSelection = (stepId: string) => {
    const step = currentState.steps.find(s => s.template.id === stepId)
    if (step) {
      updateStep(stepId, { selected: !step.selected })
    }
  }

  const hasAnyRunning = currentState.steps.some(s => s.status === 'running')
  const hasAnySelected = currentState.steps.some(s => s.selected)
  const completedSteps = currentState.steps.filter(s => s.status === 'done')
  const viewingStep = currentState.steps.find(s => s.template.id === viewingOutput)

  const statusIcon = (status: ScaffoldStepState['status']) => {
    switch (status) {
      case 'idle': return <span className="w-2 h-2 rounded-full bg-gray-300 inline-block" />
      case 'running': return <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse inline-block" />
      case 'done': return <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
      case 'error': return <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
    }
  }

  if (loadingTemplates) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-4">
        <p className="text-sm text-gray-500">Loading scaffold templates...</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-gray-900">LLM Analysis</h3>
      </div>

      {/* API Key */}
      <div className="mb-3">
        <label className="block text-xs font-medium text-gray-700 mb-1">API Key</label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="sk-..."
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Scaffold Steps */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-gray-700">Scaffold Steps</h4>
          <button
            onClick={runSelected}
            disabled={!hasAnySelected || hasAnyRunning || !apiKey.trim()}
            className="px-3 py-1 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Run Selected
          </button>
        </div>

        <div className="space-y-1 border border-gray-200 rounded-lg overflow-hidden">
          {currentState.steps.map((step) => (
            <div key={step.template.id}>
              {/* Step row */}
              <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 transition-colors">
                <input
                  type="checkbox"
                  checked={step.selected}
                  onChange={() => toggleStepSelection(step.template.id)}
                  className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded"
                />
                <button
                  className="flex-1 text-left text-sm text-gray-800 font-medium"
                  onClick={() => setExpandedStep(
                    expandedStep === step.template.id ? null : step.template.id
                  )}
                >
                  {step.template.name}
                </button>
                <span className="text-xs text-gray-500">{step.template.output_type}</span>
                {statusIcon(step.status)}
                {step.status !== 'running' && (
                  <button
                    onClick={() => runStep(step)}
                    disabled={hasAnyRunning || !apiKey.trim()}
                    className="px-2 py-0.5 text-[10px] font-medium text-blue-600 hover:text-blue-700 disabled:text-gray-400"
                  >
                    Run
                  </button>
                )}
              </div>

              {/* Expanded prompt editor */}
              {expandedStep === step.template.id && (
                <div className="px-3 py-2 bg-white border-t border-gray-100">
                  <p className="text-xs text-gray-500 mb-1">{step.template.description}</p>
                  <textarea
                    value={step.editedPrompt ?? step.template.prompt}
                    onChange={(e) => updateStep(step.template.id, { editedPrompt: e.target.value })}
                    rows={6}
                    className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  {step.error && (
                    <p className="text-xs text-red-600 mt-1">Error: {step.error}</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Output viewer */}
      {completedSteps.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-gray-700">Output</h4>
            <select
              value={viewingOutput || ''}
              onChange={(e) => setViewingOutput(e.target.value || null)}
              className="text-xs px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {completedSteps.map(s => (
                <option key={s.template.id} value={s.template.id}>
                  {s.template.name}
                </option>
              ))}
            </select>
          </div>

          {viewingStep && viewingStep.output && (
            <div className="bg-gray-50 rounded-lg p-3">
              {viewingStep.template.output_type === 'narrative' ? (
                <div className="prose prose-sm max-w-none text-gray-800">
                  <ReactMarkdown>{viewingStep.output}</ReactMarkdown>
                </div>
              ) : (
                <div className="text-sm text-gray-700">
                  <p className="font-medium mb-2">{viewingStep.output}</p>
                  {viewingStep.elementLabels && (
                    <div className="space-y-1">
                      {Object.entries(viewingStep.elementLabels).slice(0, 20).map(([key, desc]) => (
                        <div key={key} className="bg-white px-2 py-1 rounded border border-gray-200">
                          <span className="text-xs font-mono text-blue-600">{key}</span>
                          <p className="text-xs text-gray-600 mt-0.5">{desc}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
