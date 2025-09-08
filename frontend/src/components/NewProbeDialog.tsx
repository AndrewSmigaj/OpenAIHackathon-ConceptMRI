import { useState } from 'react'
import type { ProbeRequest, ProbeResponse, SessionStatus, WordSource } from '../types/api'
import { apiClient } from '../api/client'

interface NewProbeDialogProps {
  isOpen?: boolean  // Optional for backward compatibility
  onClose: () => void
  onSuccess?: (sessionId: string) => void
}

type Step = 'config' | 'sources' | 'review' | 'confirm' | 'executing'

interface WordSourceConfig {
  id: string
  type: 'contexts' | 'targets'
  source: WordSource
}

// Preset configurations for common demos
const PRESET_CONFIGS = {
  pos_contrast: {
    name: 'POS Contrast Analysis',
    description: 'Compare noun vs verb routing after "the"',
    contexts: [
      { source_type: 'custom' as const, source_params: { words: ['the'], label: 'determiner' }}
    ],
    targets: [
      { source_type: 'pos_pure' as const, source_params: { pos: 'n', max_words: 30 }},
      { source_type: 'pos_pure' as const, source_params: { pos: 'v', max_words: 30 }}
    ]
  },
  noun_complexity: {
    name: 'Noun Complexity Analysis',
    description: 'Simple vs complex noun routing patterns (100 probes)',
    contexts: [
      { source_type: 'custom' as const, source_params: { words: ['the'], label: 'determiner' }}
    ],
    targets: [
      { source_type: 'custom' as const, source_params: { 
        words: ['car', 'door', 'food', 'water', 'fire', 'sun', 'moon', 'tree', 'bird', 'fish', 
               'house', 'ball', 'hand', 'foot', 'head', 'eye', 'ear', 'nose', 'face', 'arm',
               'book', 'chair', 'table', 'bed', 'room', 'wall', 'road', 'park', 'shop', 'game',
               'cat', 'dog', 'baby', 'man', 'woman', 'boy', 'girl', 'mother', 'father', 'friend',
               'apple', 'bread', 'milk', 'cake', 'tea', 'cup', 'plate', 'knife', 'fork', 'spoon'], 
        label: 'simple_nouns' 
      }},
      { source_type: 'custom' as const, source_params: { 
        words: ['architecture', 'philosophy', 'technology', 'democracy', 'government', 'education', 'communication',
               'administration', 'organization', 'investigation', 'development', 'implementation', 'achievement', 'measurement',
               'establishment', 'arrangement', 'requirement', 'environment', 'management', 'advertisement', 'entertainment',
               'relationship', 'opportunity', 'responsibility', 'understanding', 'performance', 'temperature', 'information',
               'population', 'generation', 'destination', 'imagination', 'conversation', 'celebration', 'preparation',
               'consideration', 'recommendation', 'representation', 'transformation', 'collaboration', 'concentration',
               'demonstration', 'specification', 'documentation', 'configuration', 'authorization', 'authentication',
               'multiplication', 'construction', 'destruction', 'instruction'],
        label: 'complex_nouns' 
      }}
    ]
  },
  pos_comparison: {
    name: 'POS Comparison - Very + Adjectives/Adverbs',
    description: 'Compare adjective vs adverb routing with intensifier (100 probes)',
    contexts: [
      { source_type: 'custom' as const, source_params: { words: ['very'], label: 'intensifier' }}
    ],
    targets: [
      { source_type: 'custom' as const, source_params: { 
        words: ['adaptive', 'analytic', 'angular', 'avoidable', 'aware', 'digital', 'finite', 'illegal',
               'many', 'minimal', 'random', 'solar', 'urban', 'viral', 'allergenic', 'continental',
               'continuous', 'eligible', 'existent', 'financial', 'inclusive', 'modifiable', 'mutable',
               'optional', 'postal', 'racial', 'renal', 'semantic', 'successful', 'undefined',
               'unexpected', 'unsigned', 'unsupported', 'utile', 'vascular', 'vedic', 'cutaneous',
               'doctoral', 'forgettable', 'immutable', 'intestinal', 'ovine', 'phonic', 'precedented',
               'tractive', 'genic', 'onymous', 'otic', 'actable', 'agonal', 'biotic'], 
        label: 'adjectives' 
      }},
      { source_type: 'custom' as const, source_params: { 
        words: ['ably', 'actively', 'actually', 'afar', 'again', 'alee', 'almost', 'along',
               'already', 'also', 'always', 'amain', 'anon', 'approximately', 'around', 'astern',
               'before', 'below', 'between', 'but', 'conditionally', 'currently', 'either', 'erst',
               'especially', 'ever', 'finally', 'formerly', 'fortunately', 'fully', 'hopefully',
               'however', 'implicitly', 'infra', 'instead', 'lief', 'maybe', 'mostly', 'necessarily',
               'never', 'non', 'normally', 'not', 'oft', 'often', 'once', 'particularly', 'perhaps',
               'possibly', 'probably'], 
        label: 'adverbs' 
      }}
    ]
  },
  semantic_categories: {
    name: 'Semantic Categories',
    description: 'Animals vs artifacts routing',
    contexts: [
      { source_type: 'custom' as const, source_params: { words: ['the'], label: 'determiner' }}
    ],
    targets: [
      { source_type: 'synset_hyponyms' as const, source_params: { 
        synset_id: 'animal.n.01', max_depth: 3, unambiguous_only: false 
      }},
      { source_type: 'synset_hyponyms' as const, source_params: { 
        synset_id: 'artifact.n.01', max_depth: 3, unambiguous_only: false 
      }}
    ]
  },
  disambiguation: {
    name: 'Context Disambiguation',
    description: 'How contexts disambiguate words like "bank" (72 probes)',
    contexts: [
      { source_type: 'custom' as const, source_params: { 
        words: ['money', 'financial', 'investment'], label: 'financial' 
      }},
      { source_type: 'custom' as const, source_params: { 
        words: ['medical', 'patient', 'treatment'], label: 'medical' 
      }},
      { source_type: 'custom' as const, source_params: { 
        words: ['computer', 'software', 'network'], label: 'technology' 
      }},
      { source_type: 'custom' as const, source_params: { 
        words: ['court', 'legal', 'judge'], label: 'legal' 
      }}
    ],
    targets: [
      { source_type: 'custom' as const, source_params: { 
        words: ['bank', 'cell', 'scale', 'interest', 'court', 'patient'], label: 'ambiguous_words' 
      }}
    ]
  }
}

export default function NewProbeDialog({ isOpen = true, onClose, onSuccess }: NewProbeDialogProps) {
  const [step, setStep] = useState<Step>('config')
  const [sessionName, setSessionName] = useState('')
  const [layers, setLayers] = useState<number[]>(Array.from({length: 24}, (_, i) => i))
  const [wordSources, setWordSources] = useState<WordSourceConfig[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isExecuting, setIsExecuting] = useState(false)
  const [executionProgress, setExecutionProgress] = useState<SessionStatus | null>(null)
  
  // Store the created session info for confirmation step
  const [createdSession, setCreatedSession] = useState<ProbeResponse | null>(null)
  
  // Form state for adding new sources
  const [newSourceType, setNewSourceType] = useState<'contexts' | 'targets'>('contexts')
  const [newSourceConfig, setNewSourceConfig] = useState<'custom' | 'pos_pure' | 'synset_hyponyms'>('custom')
  const [customWords, setCustomWords] = useState('')
  const [customLabel, setCustomLabel] = useState('')
  const [posType, setPosType] = useState('n')
  const [posMaxWords, setPosMaxWords] = useState(30)
  const [synsetId, setSynsetId] = useState('')
  const [synsetDepth, setSynsetDepth] = useState(2)
  const [synsetUnambiguous, setSynsetUnambiguous] = useState(true)

  const validateSynsetId = (id: string): boolean => {
    // Basic validation for WordNet synset ID format
    return /^\w+\.[nvarsp]\.\d+$/.test(id)
  }

  const handleAddSource = () => {
    let source: WordSource | null = null
    
    switch (newSourceConfig) {
      case 'custom':
        const words = customWords.split(/[\n,]/).map(w => w.trim()).filter(w => w)
        if (words.length === 0) {
          setError('Please enter at least one word')
          return
        }
        source = {
          source_type: 'custom',
          source_params: { words, label: customLabel || 'custom' }
        }
        break
        
      case 'pos_pure':
        source = {
          source_type: 'pos_pure',
          source_params: { pos: posType, max_words: posMaxWords }
        }
        break
        
      case 'synset_hyponyms':
        if (!synsetId) {
          setError('Please enter a synset ID')
          return
        }
        if (!validateSynsetId(synsetId)) {
          setError('Invalid synset ID format. Expected: word.pos.number (e.g., animal.n.01)')
          return
        }
        source = {
          source_type: 'synset_hyponyms',
          source_params: { 
            synset_id: synsetId, 
            max_depth: synsetDepth, 
            unambiguous_only: synsetUnambiguous 
          }
        }
        break
    }
    
    if (source) {
      setWordSources([...wordSources, {
        id: Date.now().toString(),
        type: newSourceType,
        source
      }])
      
      // Reset form
      setCustomWords('')
      setCustomLabel('')
      setSynsetId('')
      setError(null)
    }
  }

  const handleRemoveSource = (id: string) => {
    setWordSources(wordSources.filter(ws => ws.id !== id))
  }

  const handleLoadPreset = (preset: keyof typeof PRESET_CONFIGS) => {
    const config = PRESET_CONFIGS[preset]
    setSessionName(config.name)
    
    const sources: WordSourceConfig[] = []
    config.contexts.forEach((source, i) => {
      sources.push({
        id: `preset-context-${i}`,
        type: 'contexts',
        source
      })
    })
    config.targets.forEach((source, i) => {
      sources.push({
        id: `preset-target-${i}`,
        type: 'targets',
        source
      })
    })
    
    setWordSources(sources)
    setStep('sources')
  }

  const getContextSources = () => wordSources.filter(ws => ws.type === 'contexts').map(ws => ws.source)
  const getTargetSources = () => wordSources.filter(ws => ws.type === 'targets').map(ws => ws.source)

  const handleCreateSession = async () => {
    setError(null)
    
    try {
      const request: ProbeRequest = {
        session_name: sessionName || `Probe Session ${new Date().toISOString()}`,
        context_sources: getContextSources(),
        target_sources: getTargetSources(),
        layers
      }
      
      // Create session to get actual probe count
      const response = await apiClient.createProbeSession(request)
      setCreatedSession(response)
      setStep('confirm')
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create probe session')
    }
  }

  const handleExecute = async () => {
    if (!createdSession) return
    
    setError(null)
    setIsExecuting(true)
    setStep('executing')
    
    try {
      // Execute the already-created session
      await apiClient.executeProbeSession(createdSession.session_id)
      
      // Poll for completion
      const finalStatus = await apiClient.pollSessionUntilComplete(
        createdSession.session_id,
        (status) => {
          setExecutionProgress(status)
        }
      )
      
      if (finalStatus.state === 'completed') {
        if (onSuccess) {
          onSuccess(finalStatus.session_id)
        }
        handleClose()
      } else if (finalStatus.state === 'failed') {
        throw new Error('Probe execution failed')
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute probe')
      setStep('confirm')
    } finally {
      setIsExecuting(false)
    }
  }

  const handleClose = () => {
    if (!isExecuting) {
      setStep('config')
      setSessionName('')
      setWordSources([])
      setError(null)
      setExecutionProgress(null)
      setCreatedSession(null)
      onClose()
    }
  }

  const renderSourceCard = (config: WordSourceConfig) => {
    const { source } = config
    let description = ''
    
    switch (source.source_type) {
      case 'custom':
        description = `${source.source_params.words?.length || 0} words (${source.source_params.label})`
        break
      case 'pos_pure':
        description = `Pure ${source.source_params.pos === 'n' ? 'nouns' : 
                             source.source_params.pos === 'v' ? 'verbs' : 
                             source.source_params.pos === 'a' ? 'adjectives' : 'adverbs'} (max ${source.source_params.max_words})`
        break
      case 'synset_hyponyms':
        description = `${source.source_params.synset_id} (depth ${source.source_params.max_depth}, ${source.source_params.unambiguous_only ? 'unambiguous' : 'all'})`
        break
    }
    
    return (
      <div key={config.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <div>
          <span className="font-medium capitalize">{config.type}: </span>
          <span className="text-gray-600">{description}</span>
        </div>
        <button
          onClick={() => handleRemoveSource(config.id)}
          className="text-red-500 hover:text-red-700"
        >
          Remove
        </button>
      </div>
    )
  }

  const getEstimatedTime = (probeCount: number): string => {
    // Rough estimate: ~3-4 seconds per probe
    const seconds = probeCount * 3.5
    if (seconds < 60) {
      return `${Math.round(seconds)} seconds`
    } else if (seconds < 3600) {
      return `${Math.round(seconds / 60)} minutes`
    } else {
      return `${Math.round(seconds / 3600)} hours`
    }
  }

  // Early return if not open (for backward compatibility with modal usage)
  if (isOpen === false) return null

  return (
    <div className="space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {step === 'config' && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Session Name
              </label>
              <input
                type="text"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                placeholder="e.g., POS Contrast Analysis"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Layers to Capture
              </label>
              <div className="flex gap-2">
                {[0, 1, 2, 3, 4, 5].map(layer => (
                  <label key={layer} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={layers.includes(layer)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setLayers([...layers, layer].sort())
                        } else {
                          setLayers(layers.filter(l => l !== layer))
                        }
                      }}
                      className="mr-1"
                    />
                    {layer}
                  </label>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1">Default: [0, 1, 2] for first window</p>
            </div>

            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Quick Start Presets</p>
              <div className="space-y-2">
                {Object.entries(PRESET_CONFIGS).map(([key, config]) => (
                  <button
                    key={key}
                    onClick={() => handleLoadPreset(key as keyof typeof PRESET_CONFIGS)}
                    className="w-full text-left p-3 border rounded-lg hover:bg-gray-50"
                  >
                    <p className="font-medium">{config.name}</p>
                    <p className="text-sm text-gray-600">{config.description}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setStep('sources')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Next: Add Word Sources
              </button>
            </div>
          </>
        )}

        {step === 'sources' && (
          <>
            <div>
              <h3 className="font-medium text-gray-900 mb-3">Current Word Sources</h3>
              <div className="space-y-2 mb-4">
                {wordSources.length === 0 ? (
                  <p className="text-gray-500 text-sm">No sources added yet</p>
                ) : (
                  <>
                    <p className="text-sm text-gray-600">Contexts:</p>
                    {wordSources.filter(ws => ws.type === 'contexts').map(renderSourceCard)}
                    <p className="text-sm text-gray-600 mt-3">Targets:</p>
                    {wordSources.filter(ws => ws.type === 'targets').map(renderSourceCard)}
                  </>
                )}
              </div>
            </div>

            <div className="border-t pt-4">
              <h3 className="font-medium text-gray-900 mb-3">Add New Source</h3>
              
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                  <select
                    value={newSourceType}
                    onChange={(e) => setNewSourceType(e.target.value as 'contexts' | 'targets')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="contexts">Contexts</option>
                    <option value="targets">Targets</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Source</label>
                  <select
                    value={newSourceConfig}
                    onChange={(e) => setNewSourceConfig(e.target.value as any)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="custom">Custom List</option>
                    <option value="pos_pure">POS-Pure Words</option>
                    <option value="synset_hyponyms">WordNet Synset</option>
                  </select>
                </div>
              </div>

              {newSourceConfig === 'custom' && (
                <>
                  <div className="mb-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Words (comma or newline separated)
                    </label>
                    <textarea
                      value={customWords}
                      onChange={(e) => setCustomWords(e.target.value)}
                      placeholder="cat, dog, mouse\nor one per line"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg h-20"
                    />
                  </div>
                  <div className="mb-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Category Label
                    </label>
                    <input
                      type="text"
                      value={customLabel}
                      onChange={(e) => setCustomLabel(e.target.value)}
                      placeholder="e.g., animals"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    />
                  </div>
                </>
              )}

              {newSourceConfig === 'pos_pure' && (
                <>
                  <div className="mb-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Part of Speech
                    </label>
                    <select
                      value={posType}
                      onChange={(e) => setPosType(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value="n">Nouns</option>
                      <option value="v">Verbs</option>
                      <option value="a">Adjectives</option>
                      <option value="r">Adverbs</option>
                    </select>
                  </div>
                  <div className="mb-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Max Words: {posMaxWords}
                    </label>
                    <input
                      type="range"
                      min="10"
                      max="100"
                      value={posMaxWords}
                      onChange={(e) => setPosMaxWords(Number(e.target.value))}
                      className="w-full"
                    />
                  </div>
                </>
              )}

              {newSourceConfig === 'synset_hyponyms' && (
                <>
                  <div className="mb-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Synset ID
                    </label>
                    <input
                      type="text"
                      value={synsetId}
                      onChange={(e) => setSynsetId(e.target.value)}
                      placeholder="e.g., animal.n.01"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Common: animal.n.01, artifact.n.01, color.n.01, emotion.n.01
                    </p>
                  </div>
                  <div className="mb-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Max Depth: {synsetDepth}
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="5"
                      value={synsetDepth}
                      onChange={(e) => setSynsetDepth(Number(e.target.value))}
                      className="w-full"
                    />
                  </div>
                  <div className="mb-3">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={synsetUnambiguous}
                        onChange={(e) => setSynsetUnambiguous(e.target.checked)}
                        className="mr-2"
                      />
                      Unambiguous words only
                    </label>
                    <p className="text-xs text-gray-500 mt-1">
                      Filter to words with single meaning
                    </p>
                  </div>
                </>
              )}

              <button
                onClick={handleAddSource}
                className="w-full px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Add Source
              </button>
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setStep('config')}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Back
              </button>
              <button
                onClick={() => setStep('review')}
                disabled={wordSources.length === 0}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                Next: Review
              </button>
            </div>
          </>
        )}

        {step === 'review' && (
          <>
            <div>
              <h3 className="font-medium text-gray-900 mb-3">Review Configuration</h3>
              
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-gray-700">Session Name</p>
                  <p className="text-gray-900">{sessionName || 'Unnamed Session'}</p>
                </div>
                
                <div>
                  <p className="text-sm font-medium text-gray-700">Layers</p>
                  <p className="text-gray-900">[{layers.join(', ')}]</p>
                </div>
                
                <div>
                  <p className="text-sm font-medium text-gray-700">Context Sources</p>
                  <div className="space-y-1">
                    {wordSources.filter(ws => ws.type === 'contexts').map(renderSourceCard)}
                  </div>
                </div>
                
                <div>
                  <p className="text-sm font-medium text-gray-700">Target Sources</p>
                  <div className="space-y-1">
                    {wordSources.filter(ws => ws.type === 'targets').map(renderSourceCard)}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setStep('sources')}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Back
              </button>
              <button
                onClick={handleCreateSession}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Create Session
              </button>
            </div>
          </>
        )}

        {step === 'confirm' && createdSession && (
          <>
            <div>
              <h3 className="font-medium text-gray-900 mb-3">Session Created Successfully!</h3>
              
              <div className="space-y-3">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-green-900 font-medium">
                    Session ID: {createdSession.session_id}
                  </p>
                </div>
                
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-blue-900 font-medium text-lg">
                    Actual Probe Count: {createdSession.total_pairs} probes
                  </p>
                  <p className="text-blue-700 text-sm mt-1">
                    Estimated capture time: {getEstimatedTime(createdSession.total_pairs)}
                  </p>
                </div>
                
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Actual Contexts ({createdSession.contexts.length}):</p>
                  <div className="max-h-32 overflow-y-auto bg-gray-50 rounded p-2">
                    <p className="text-xs text-gray-600">
                      {createdSession.contexts.join(', ')}
                    </p>
                  </div>
                </div>
                
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Actual Targets ({createdSession.targets.length}):</p>
                  <div className="max-h-32 overflow-y-auto bg-gray-50 rounded p-2">
                    <p className="text-xs text-gray-600">
                      {createdSession.targets.slice(0, 50).join(', ')}
                      {createdSession.targets.length > 50 && ` ... and ${createdSession.targets.length - 50} more`}
                    </p>
                  </div>
                </div>

                {createdSession.total_pairs > 500 && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                    <p className="text-yellow-800 text-sm">
                      ⚠️ This is a large probe set. Execution may take {getEstimatedTime(createdSession.total_pairs)}.
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => {
                  setCreatedSession(null)
                  setStep('review')
                }}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Back to Edit
              </button>
              <button
                onClick={handleExecute}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Execute Capture ({createdSession.total_pairs} probes)
              </button>
            </div>
          </>
        )}

        {step === 'executing' && (
          <div className="py-8 text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-900 font-medium">Capturing MoE activations...</p>
            
            {executionProgress && (
              <div className="mt-4">
                <p className="text-sm text-gray-600">
                  Progress: {executionProgress.progress.completed} / {executionProgress.progress.total}
                </p>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${(executionProgress.progress.completed / executionProgress.progress.total) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  {executionProgress.state === 'running' 
                    ? `Estimated time remaining: ${getEstimatedTime(executionProgress.progress.total - executionProgress.progress.completed)}`
                    : executionProgress.state
                  }
                </p>
              </div>
            )}
          </div>
        )}
      </div>
  )
}