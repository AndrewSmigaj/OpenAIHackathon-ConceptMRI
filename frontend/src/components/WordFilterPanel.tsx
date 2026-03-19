import { useMemo } from 'react'
import type { SessionDetailResponse } from '../types/api'

export interface FilterState {
  labels: Set<string>
}

interface WordFilterPanelProps {
  sessionData: SessionDetailResponse | null
  selectedFilters: FilterState
  onFiltersChange: (filters: FilterState) => void
  isLoading?: boolean
  availableRegimeLabels?: string[]
}

export default function WordFilterPanel({
  sessionData,
  selectedFilters,
  onFiltersChange,
  isLoading = false,
  availableRegimeLabels = []
}: WordFilterPanelProps) {

  const { availableLabels, totalProbes, filteredProbes } = useMemo(() => {
    if (!sessionData) {
      return { availableLabels: [] as string[], totalProbes: 0, filteredProbes: 0 }
    }

    const labels = sessionData.labels || []
    const total = sessionData.manifest?.probe_count || 0

    // When no labels selected, show all
    const filtered = selectedFilters.labels.size === 0
      ? total
      : total // Approximate — server does the real filtering

    return {
      availableLabels: labels,
      totalProbes: total,
      filteredProbes: filtered
    }
  }, [sessionData, selectedFilters])

  const handleLabelToggle = (label: string) => {
    const newLabels = new Set(selectedFilters.labels)
    if (newLabels.has(label)) {
      newLabels.delete(label)
    } else {
      newLabels.add(label)
    }

    onFiltersChange({
      ...selectedFilters,
      labels: newLabels
    })
  }

  const handleSelectAll = () => {
    onFiltersChange({
      ...selectedFilters,
      labels: new Set(availableLabels)
    })
  }

  const handleClearAll = () => {
    onFiltersChange({
      ...selectedFilters,
      labels: new Set()
    })
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded mb-4"></div>
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
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

  return (
    <div className="bg-white rounded-xl shadow-md p-6 space-y-6">
      <div>
        <h4 className="font-medium text-gray-900 mb-4">Filters</h4>

        {/* Target Word */}
        {sessionData.target_word && (
          <div className="mb-4">
            <p className="text-sm text-gray-600">
              Target word: <span className="font-semibold text-gray-900">{sessionData.target_word}</span>
            </p>
          </div>
        )}

        {/* Labels */}
        {availableLabels.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h5 className="text-sm font-medium text-gray-700">Labels</h5>
              <span className="text-xs text-gray-500">({availableLabels.length})</span>
            </div>

            <div className="space-y-2 max-h-32 overflow-y-auto">
              {availableLabels.map(label => (
                <label key={label} className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedFilters.labels.has(label)}
                    onChange={() => handleLabelToggle(label)}
                    className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
                  />
                  <span className="ml-3 text-sm text-gray-700 capitalize">
                    {label}
                  </span>
                </label>
              ))}
            </div>

            <div className="flex gap-2 mt-3">
              <button
                onClick={handleSelectAll}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
              >
                Select All
              </button>
              <button
                onClick={handleClearAll}
                className="text-xs text-gray-600 hover:text-gray-700 font-medium"
              >
                Clear All
              </button>
            </div>
          </div>
        )}

        {/* Filter Summary */}
        <div className="pt-4 border-t border-gray-200">
          <div className="bg-gray-50 rounded-xl p-3">
            <p className="text-sm text-gray-600">
              {totalProbes} probes total
            </p>
            {selectedFilters.labels.size > 0 && (
              <p className="text-xs text-gray-500 mt-1">
                Labels: {Array.from(selectedFilters.labels).join(', ')}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
