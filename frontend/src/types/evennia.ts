/** Room context sent via OOB room_entered event */
export interface RoomContext {
  role: 'researcher' | 'visitor'
  roomType: 'lab' | 'micro_world' | 'hub' | 'social'
}

/** Viz preset fields that map to React hook setters */
export interface VizPreset {
  primary_axis?: string
  gradient?: string
  window?: string
  clustering_schema?: string
  top_routes?: number
}

/** OOB room_entered payload from Evennia */
export interface RoomEnteredPayload {
  room_type: string
  role: string
  session_id?: string | null
  clustering_schema?: string
  viz_preset?: VizPreset
}

/** OOB room_left payload from Evennia */
export interface RoomLeftPayload {
  room_type: string
}
