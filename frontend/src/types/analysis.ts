import type { SankeyNode, SankeyLink } from './api'

export type SelectedCard =
  | { type: 'expert'; data: SankeyNode & Record<string, any> }
  | { type: 'highway'; data: SankeyLink & Record<string, any> }
  | { type: 'cluster'; data: SankeyNode & Record<string, any> }
  | { type: 'route'; data: SankeyLink & Record<string, any> }
