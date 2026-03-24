import { useState, useEffect } from 'react'
import { apiClient } from '../api/client'

export interface SchemaManagementState {
  availableSchemas: Array<{ name: string; created_at: string; params: any }>
  selectedSchema: string
  schemaReports: Record<string, string>
  setSelectedSchema: React.Dispatch<React.SetStateAction<string>>
}

export function useSchemaManagement(
  selectedSessions: string[],
  onElementDescriptionsLoaded: (descs: Record<string, string>) => void,
): SchemaManagementState {
  const [availableSchemas, setAvailableSchemas] = useState<Array<{ name: string; created_at: string; params: any }>>([])
  const [selectedSchema, setSelectedSchema] = useState<string>('')
  const [schemaReports, setSchemaReports] = useState<Record<string, string>>({})

  // Fetch available schemas when sessions change
  useEffect(() => {
    if (selectedSessions.length === 1) {
      apiClient.listClusterings(selectedSessions[0]).then(res => {
        setAvailableSchemas(res.clusterings || [])
      }).catch(() => setAvailableSchemas([]))
    } else {
      setAvailableSchemas([])
    }
    setSelectedSchema('')
  }, [selectedSessions])

  // Load reports and element descriptions when schema is selected
  useEffect(() => {
    if (selectedSchema && selectedSessions.length > 0) {
      apiClient.getClusteringDetails(selectedSessions[0], selectedSchema)
        .then(d => {
          setSchemaReports(d.reports || {})
          if (d.element_descriptions) {
            onElementDescriptionsLoaded(d.element_descriptions)
          }
        })
        .catch(() => setSchemaReports({}))
    } else {
      setSchemaReports({})
    }
  }, [selectedSchema, selectedSessions, onElementDescriptionsLoaded])

  return { availableSchemas, selectedSchema, schemaReports, setSelectedSchema }
}
