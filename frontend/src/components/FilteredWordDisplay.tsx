import type { SessionDetailResponse } from '../types/api'
import type { FilterState } from './WordFilterPanel'
import type { GradientScheme } from '../utils/colorBlending'
import { getNodeColor } from '../utils/colorBlending'
import SentenceHighlight from './SentenceHighlight'

interface FilteredWordDisplayProps {
  sessionData: SessionDetailResponse | null
  filterState: FilterState
  isLoading?: boolean
  colorLabelA: string
  colorLabelB: string
  gradient: GradientScheme
}

export default function FilteredWordDisplay({
  sessionData,
  filterState,
  isLoading = false,
  colorLabelA,
  colorLabelB,
  gradient
}: FilteredWordDisplayProps) {

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded mb-4"></div>
          <div className="space-y-2">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-3 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!sessionData) {
    return (
      <div className="bg-white rounded-xl shadow-md p-6">
        <p className="text-gray-500 text-sm">No session data available</p>
      </div>
    )
  }

  const hasFilters = filterState.labels.size > 0
  const sentences = (sessionData.sentences || []).filter(s => {
    if (!hasFilters) return true
    return s.label ? filterState.labels.has(s.label) : false
  })

  return (
    <div className="bg-white rounded-xl shadow-md p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-gray-900 text-sm">
          Sentences
        </h4>
        <span className="text-xs text-gray-500">
          {sentences.length}{hasFilters ? ' filtered' : ''}
        </span>
      </div>

      {/* Target Word */}
      {sessionData.target_word && (
        <div>
          <span className="text-xs text-gray-500">Target: </span>
          <span className="text-sm font-semibold text-gray-900">{sessionData.target_word}</span>
        </div>
      )}

      {/* Sentence List */}
      {sentences.length > 0 ? (
        <div className="space-y-2 max-h-[60vh] overflow-y-auto">
          {sentences.map((sentence, i) => {
            const color = sentence.label && colorLabelA && colorLabelB
              ? getNodeColor({ [sentence.label]: 1 }, colorLabelA, colorLabelB, undefined, undefined, gradient)
              : '#666666'

            return (
              <div key={sentence.probe_id || i} className="bg-gray-50 rounded-lg p-2">
                <div className="flex items-center gap-1.5 mb-1">
                  {sentence.label && (
                    <span
                      className="px-1.5 py-0.5 text-[10px] font-medium rounded-full text-white capitalize"
                      style={{ backgroundColor: color }}
                    >
                      {sentence.label}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-700 leading-relaxed">
                  <SentenceHighlight
                    text={sentence.input_text}
                    targetWord={sentence.target_word}
                    color={color}
                  />
                </p>
              </div>
            )
          })}
        </div>
      ) : (
        <p className="text-xs text-gray-500">
          {hasFilters ? 'No sentences match the current filters' : 'No sentences available'}
        </p>
      )}
    </div>
  )
}
