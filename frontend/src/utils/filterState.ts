import type { FilterState } from '../components/WordFilterPanel'
import type { AnalyzeRoutesRequest } from '../types/api'

/**
 * Convert frontend FilterState to backend filter_config format.
 * Empty sets mean "include all" (no filtering), so we return undefined.
 */
export function convertFilterState(
  filterState: FilterState,
): AnalyzeRoutesRequest['filter_config'] {
  const filterConfig: any = {}

  if (filterState.labels.size > 0) {
    filterConfig.labels = Array.from(filterState.labels)
  }

  return Object.keys(filterConfig).length > 0 ? filterConfig : undefined
}
