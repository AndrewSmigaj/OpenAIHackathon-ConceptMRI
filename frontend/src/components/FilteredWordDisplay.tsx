import type { SessionDetailResponse } from '../types/api'
import type { FilterState } from './WordFilterPanel'
import type { GradientScheme } from '../utils/colorBlending'
import { getNodeColor } from '../utils/colorBlending'
import SentenceHighlight from './SentenceHighlight'

interface FilteredWordDisplayProps {
  sessionData: SessionDetailResponse | null
  filterState: FilterState
  isLoading?: boolean
  primaryValues: string[]
  gradient: GradientScheme
}

export default function FilteredWordDisplay({
  sessionData,
  filterState,
  isLoading = false,
  primaryValues,
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
    <div className="bg-white rounded-xl shadow-md p-2 space-y-1">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-gray-900 text-xs">
          Sentences {sessionData.target_word && <span className="text-gray-500 font-normal">— {sessionData.target_word}</span>}
        </h4>
        <span className="text-[10px] text-gray-500">
          {sentences.length}{hasFilters ? ' filtered' : ''}
        </span>
      </div>

      {/* Sentence List */}
      {sentences.length > 0 ? (
        <div className="space-y-0.5 max-h-[75vh] overflow-y-auto">
          {sentences.map((sentence, i) => {
            const color = sentence.label && primaryValues.length > 0
              ? getNodeColor({ [sentence.label]: 1 }, primaryValues, gradient)
              : '#666666'

            return (
              <div key={sentence.probe_id || i} className="bg-gray-50 rounded px-1.5 py-1">
                <p className="text-[10px] text-gray-700 leading-snug">
                  {sentence.label && (
                    <span
                      className="inline-block px-1 py-px text-[8px] font-medium rounded text-white capitalize mr-1 align-middle"
                      style={{ backgroundColor: color }}
                    >
                      {sentence.label}
                    </span>
                  )}
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
        <p className="text-[10px] text-gray-500">
          {hasFilters ? 'No sentences match the current filters' : 'No sentences available'}
        </p>
      )}
    </div>
  )
}
