import { useMemo } from 'react'
import type { SessionDetailResponse } from '../types/api'
import type { FilterState } from './WordFilterPanel'

interface FilteredWordDisplayProps {
  sessionData: SessionDetailResponse | null
  filterState: FilterState
  isLoading?: boolean
}

export default function FilteredWordDisplay({ 
  sessionData, 
  filterState, 
  isLoading = false 
}: FilteredWordDisplayProps) {

  // Compute filtered words
  const { contextWords, targetWords, totalPairs } = useMemo(() => {
    if (!sessionData) {
      return { contextWords: [], targetWords: [], totalPairs: 0 }
    }

    // Helper function to check if word matches selected filters
    const shouldIncludeContextWord = (word: string): boolean => {
      if (filterState.contextCategories.size === 0) return true
      const categories = sessionData.categories.contexts[word] || []
      return categories.some(cat => filterState.contextCategories.has(cat))
    }

    const shouldIncludeTargetWord = (word: string): boolean => {
      if (filterState.targetCategories.size === 0) return true
      const categories = sessionData.categories.targets[word] || []
      return categories.some(cat => filterState.targetCategories.has(cat))
    }

    // Get filtered context words with their categories
    const filteredContextWords = Object.keys(sessionData.categories.contexts)
      .filter(shouldIncludeContextWord)
      .map(word => ({
        word,
        categories: sessionData.categories.contexts[word] || []
      }))
      .sort((a, b) => a.word.localeCompare(b.word))

    // Get filtered target words with their categories
    const filteredTargetWords = Object.keys(sessionData.categories.targets)
      .filter(shouldIncludeTargetWord)
      .map(word => ({
        word,
        categories: sessionData.categories.targets[word] || []
      }))
      .sort((a, b) => a.word.localeCompare(b.word))

    // Calculate total possible pairs from filtered words
    const totalFilteredPairs = filteredContextWords.length * filteredTargetWords.length

    return {
      contextWords: filteredContextWords,
      targetWords: filteredTargetWords,
      totalPairs: totalFilteredPairs
    }
  }, [sessionData, filterState])

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

  const hasFilters = filterState.contextCategories.size > 0 || filterState.targetCategories.size > 0

  return (
    <div className="bg-white rounded-xl shadow-md p-6 space-y-6">
      <div>
        <h4 className="font-medium text-gray-900 mb-4">
          {hasFilters ? 'Filtered Words' : 'All Words'}
        </h4>

        {/* Context Words */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h5 className="text-sm font-medium text-gray-700">Context Words</h5>
            <span className="text-xs text-gray-500">({contextWords.length})</span>
          </div>
          
          <div className="max-h-40 overflow-y-auto">
            {contextWords.length > 0 ? (
              <div className="space-y-1">
                {contextWords.map(({ word, categories }) => (
                  <div key={word} className="text-sm">
                    <span className="font-medium text-gray-900">"{word}"</span>
                    <span className="text-gray-500 ml-2">
                      [{categories.join(', ')}]
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 italic">No matching context words</p>
            )}
          </div>
        </div>

        {/* Target Words */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h5 className="text-sm font-medium text-gray-700">Target Words</h5>
            <span className="text-xs text-gray-500">({targetWords.length})</span>
          </div>
          
          <div className="max-h-40 overflow-y-auto">
            {targetWords.length > 0 ? (
              <div className="space-y-1">
                {targetWords.map(({ word, categories }) => (
                  <div key={word} className="text-sm">
                    <span className="font-medium text-gray-900">"{word}"</span>
                    <span className="text-gray-500 ml-2">
                      [{categories.join(', ')}]
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 italic">No matching target words</p>
            )}
          </div>
        </div>

        {/* Summary */}
        <div className="pt-4 border-t border-gray-200">
          <div className="bg-gray-50 rounded-xl p-3">
            <p className="text-sm text-gray-600">
              <span className="font-medium">{totalPairs}</span> possible pairs
              {hasFilters ? ' (filtered)' : ' (all)'}
            </p>
          </div>
        </div>

        {/* Filter Status */}
        {!hasFilters && (
          <div className="pt-3">
            <p className="text-xs text-blue-600">
              💡 Select categories in Word Filters to see filtered results
            </p>
          </div>
        )}
      </div>
    </div>
  )
}