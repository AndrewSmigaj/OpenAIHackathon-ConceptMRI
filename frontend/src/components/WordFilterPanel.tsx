import { useMemo } from 'react'
import type { SessionDetailResponse } from '../types/api'

export interface FilterState {
  contextCategories: Set<string>
  targetCategories: Set<string>
}

interface WordFilterPanelProps {
  sessionData: SessionDetailResponse | null
  selectedFilters: FilterState
  onFiltersChange: (filters: FilterState) => void
  isLoading?: boolean
}

interface CategoryInfo {
  name: string
  wordCount: number
}

export default function WordFilterPanel({ 
  sessionData, 
  selectedFilters, 
  onFiltersChange, 
  isLoading = false 
}: WordFilterPanelProps) {
  
  // Compute category counts from original backend data
  const { contextCategories, targetCategories, totalPairs, filteredPairs } = useMemo(() => {
    if (!sessionData) {
      return { contextCategories: [], targetCategories: [], totalPairs: 0, filteredPairs: 0 }
    }

    // Count how many words belong to each context category
    const contextCounts = new Map<string, number>()
    Object.values(sessionData.categories.contexts).flat().forEach(category => {
      contextCounts.set(category, (contextCounts.get(category) || 0) + 1)
    })
    const contextCats: CategoryInfo[] = Array.from(contextCounts.entries())
      .map(([name, wordCount]) => ({ name, wordCount }))
      .sort((a, b) => a.name.localeCompare(b.name))

    // Count how many words belong to each target category
    const targetCounts = new Map<string, number>()
    Object.values(sessionData.categories.targets).flat().forEach(category => {
      targetCounts.set(category, (targetCounts.get(category) || 0) + 1)
    })
    const targetCats: CategoryInfo[] = Array.from(targetCounts.entries())
      .map(([name, wordCount]) => ({ name, wordCount }))
      .sort((a, b) => a.name.localeCompare(b.name))

    // Calculate total possible context-target pairs
    const contextWords = Object.keys(sessionData.categories.contexts)
    const targetWords = Object.keys(sessionData.categories.targets)
    const total = contextWords.length * targetWords.length

    // Calculate filtered pairs using inline filtering logic
    let filtered = 0
    contextWords.forEach(contextWord => {
      targetWords.forEach(targetWord => {
        const contextCategories = sessionData.categories.contexts[contextWord] || []
        const targetCategories = sessionData.categories.targets[targetWord] || []
        
        // Include if word has ANY selected category (or no filters selected)
        const contextMatch = selectedFilters.contextCategories.size === 0 || 
          contextCategories.some(cat => selectedFilters.contextCategories.has(cat))
        const targetMatch = selectedFilters.targetCategories.size === 0 || 
          targetCategories.some(cat => selectedFilters.targetCategories.has(cat))
          
        if (contextMatch && targetMatch) {
          filtered++
        }
      })
    })

    return { 
      contextCategories: contextCats, 
      targetCategories: targetCats, 
      totalPairs: total,
      filteredPairs: filtered
    }
  }, [sessionData, selectedFilters])

  const handleContextToggle = (categoryName: string) => {
    const newContexts = new Set(selectedFilters.contextCategories)
    if (newContexts.has(categoryName)) {
      newContexts.delete(categoryName)
    } else {
      newContexts.add(categoryName)
    }
    
    onFiltersChange({
      ...selectedFilters,
      contextCategories: newContexts
    })
  }

  const handleTargetToggle = (categoryName: string) => {
    const newTargets = new Set(selectedFilters.targetCategories)
    if (newTargets.has(categoryName)) {
      newTargets.delete(categoryName)
    } else {
      newTargets.add(categoryName)
    }
    
    onFiltersChange({
      ...selectedFilters,
      targetCategories: newTargets
    })
  }

  const handleSelectAllContexts = () => {
    onFiltersChange({
      ...selectedFilters,
      contextCategories: new Set(contextCategories.map(c => c.name))
    })
  }

  const handleClearAllContexts = () => {
    onFiltersChange({
      ...selectedFilters,
      contextCategories: new Set()
    })
  }

  const handleSelectAllTargets = () => {
    onFiltersChange({
      ...selectedFilters,
      targetCategories: new Set(targetCategories.map(c => c.name))
    })
  }

  const handleClearAllTargets = () => {
    onFiltersChange({
      ...selectedFilters,
      targetCategories: new Set()
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
        <h4 className="font-medium text-gray-900 mb-4">Word Filters</h4>
        
        {/* Context Categories */}
        {contextCategories.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h5 className="text-sm font-medium text-gray-700">Context Categories</h5>
              <span className="text-xs text-gray-500">({contextCategories.length})</span>
            </div>
            
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {contextCategories.map(category => (
                <label key={category.name} className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedFilters.contextCategories.has(category.name)}
                    onChange={() => handleContextToggle(category.name)}
                    className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
                  />
                  <div className="ml-3 flex items-center">
                    {/* TODO: Add color dot indicator */}
                    <span className="text-sm text-gray-700 capitalize">
                      {category.name} ({category.wordCount})
                    </span>
                  </div>
                </label>
              ))}
            </div>
            
            <div className="flex gap-2 mt-3">
              <button
                onClick={handleSelectAllContexts}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
              >
                Select All
              </button>
              <button
                onClick={handleClearAllContexts}
                className="text-xs text-gray-600 hover:text-gray-700 font-medium"
              >
                Clear All
              </button>
            </div>
          </div>
        )}

        {/* Target Categories */}
        {targetCategories.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h5 className="text-sm font-medium text-gray-700">Target Categories</h5>
              <span className="text-xs text-gray-500">({targetCategories.length})</span>
            </div>
            
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {targetCategories.map(category => (
                <label key={category.name} className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedFilters.targetCategories.has(category.name)}
                    onChange={() => handleTargetToggle(category.name)}
                    className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
                  />
                  <div className="ml-3 flex items-center">
                    {/* TODO: Add color dot indicator */}
                    <span className="text-sm text-gray-700 capitalize">
                      {category.name} ({category.wordCount})
                    </span>
                  </div>
                </label>
              ))}
            </div>
            
            <div className="flex gap-2 mt-3">
              <button
                onClick={handleSelectAllTargets}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
              >
                Select All
              </button>
              <button
                onClick={handleClearAllTargets}
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
              Showing <span className="font-medium">{filteredPairs}</span> / <span className="font-medium">{totalPairs}</span> pairs
            </p>
            {selectedFilters.contextCategories.size > 0 && (
              <p className="text-xs text-gray-500 mt-1">
                Contexts: {Array.from(selectedFilters.contextCategories).join(', ')}
              </p>
            )}
            {selectedFilters.targetCategories.size > 0 && (
              <p className="text-xs text-gray-500 mt-1">
                Targets: {Array.from(selectedFilters.targetCategories).join(', ')}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}