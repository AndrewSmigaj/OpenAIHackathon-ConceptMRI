// @ts-ignore
import jStat from 'jStat'

interface SankeyNode {
  name: string
  id: string
  layer: number
  token_count: number
}

interface SankeyLink {
  source: string
  target: string
  value: number
}

interface WindowAnalysisProps {
  routeData: {
    nodes: SankeyNode[]
    links: SankeyLink[]
    statistics?: { total_probes?: number }
  } | null
  windowLabel?: string
}

interface ContingencyResult {
  table: { source: string; outcomes: Record<string, number>; total: number }[]
  outcomeLabels: string[]
  chiSquare: number
  pValue: number
  cramersV: number
  isSignificant: boolean
  n: number
}

function computeContingency(nodes: SankeyNode[], links: SankeyLink[]): ContingencyResult | null {
  // Find output nodes and the links feeding into them
  const outNodes = nodes.filter(n => n.name.startsWith('Out:'))
  if (outNodes.length < 2) return null

  const outLinks = links.filter(l => l.target.startsWith('Out:'))
  if (outLinks.length === 0) return null

  // Source nodes = unique sources of output links
  const sourceNames = [...new Set(outLinks.map(l => l.source))]
  const outcomeLabels = outNodes.map(n => n.name.replace('Out:', ''))

  // Build contingency table
  const table = sourceNames.map(src => {
    const outcomes: Record<string, number> = {}
    let total = 0
    for (const label of outcomeLabels) {
      const link = outLinks.find(l => l.source === src && l.target === `Out:${label}`)
      const val = link?.value ?? 0
      outcomes[label] = val
      total += val
    }
    return { source: src, outcomes, total }
  })

  // Total N
  const n = table.reduce((s, r) => s + r.total, 0)
  if (n === 0) return null

  // Column totals
  const colTotals: Record<string, number> = {}
  for (const label of outcomeLabels) {
    colTotals[label] = table.reduce((s, r) => s + (r.outcomes[label] ?? 0), 0)
  }

  // Chi-square test of independence
  let chiSquare = 0
  const r = table.length
  const c = outcomeLabels.length

  for (const row of table) {
    for (const label of outcomeLabels) {
      const observed = row.outcomes[label] ?? 0
      const expected = (row.total * colTotals[label]) / n
      if (expected > 0) {
        chiSquare += Math.pow(observed - expected, 2) / expected
      }
    }
  }

  const df = (r - 1) * (c - 1)
  const pValue = df > 0 ? 1 - jStat.chisquare.cdf(chiSquare, df) : 1
  const cramersV = df > 0 ? Math.sqrt(chiSquare / (n * Math.min(r - 1, c - 1))) : 0

  return {
    table,
    outcomeLabels,
    chiSquare,
    pValue,
    cramersV,
    isSignificant: pValue < 0.05,
    n,
  }
}

function strengthLabel(v: number): string {
  if (v < 0.1) return 'negligible'
  if (v < 0.3) return 'small'
  if (v < 0.5) return 'moderate'
  return 'strong'
}

export default function WindowAnalysis({ routeData, windowLabel }: WindowAnalysisProps) {
  if (!routeData) {
    return (
      <div className="bg-gray-50 rounded p-2 mb-2">
        <p className="text-[10px] text-gray-400 italic">Run analysis to see window statistics</p>
      </div>
    )
  }

  const result = computeContingency(routeData.nodes, routeData.links)

  if (!result) {
    return (
      <div className="bg-gray-50 rounded p-2 mb-2">
        <p className="text-[10px] text-gray-400 italic">No output nodes to analyze</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded border border-gray-200 p-2 mb-2" style={{ overflowWrap: 'break-word' }}>
      {windowLabel && (
        <p className="text-[11px] font-semibold text-gray-700 mb-1.5">{windowLabel}</p>
      )}

      {/* Contingency Table */}
      <table className="w-full text-[10px] mb-1.5">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left text-gray-500 py-0.5 pr-1"></th>
            {result.outcomeLabels.map(label => (
              <th key={label} className="text-right text-gray-500 py-0.5 px-1 capitalize">{label}</th>
            ))}
            <th className="text-right text-gray-400 py-0.5 pl-1">n</th>
          </tr>
        </thead>
        <tbody>
          {result.table.map(row => (
            <tr key={row.source} className="border-b border-gray-100">
              <td className="text-gray-700 font-medium py-0.5 pr-1 truncate max-w-[60px]">{row.source}</td>
              {result.outcomeLabels.map(label => {
                const val = row.outcomes[label] ?? 0
                const pct = row.total > 0 ? ((val / row.total) * 100).toFixed(0) : '0'
                return (
                  <td key={label} className="text-right text-gray-800 py-0.5 px-1">
                    {val} <span className="text-gray-400">({pct}%)</span>
                  </td>
                )
              })}
              <td className="text-right text-gray-400 py-0.5 pl-1">{row.total}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Stats */}
      <div className="space-y-0.5 text-[10px]">
        <div className="flex justify-between">
          <span className="text-gray-500">χ²({(result.table.length - 1) * (result.outcomeLabels.length - 1)})</span>
          <span className="font-mono text-gray-800">{result.chiSquare.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">p-value</span>
          <span className={`font-mono ${result.isSignificant ? 'text-green-700 font-semibold' : 'text-gray-800'}`}>
            {result.pValue < 0.001 ? '<0.001' : result.pValue.toFixed(4)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Cramer's V</span>
          <span className="font-mono text-gray-800">{result.cramersV.toFixed(3)} ({strengthLabel(result.cramersV)})</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Significant</span>
          <span className={`font-semibold ${result.isSignificant ? 'text-green-600' : 'text-red-500'}`}>
            {result.isSignificant ? 'Yes' : 'No'}
          </span>
        </div>
      </div>

      {/* Per-source outcome summary */}
      <div className="mt-1.5 pt-1.5 border-t border-gray-100 space-y-0.5">
        {result.table.map(row => {
          const dominant = result.outcomeLabels.reduce((best, label) =>
            (row.outcomes[label] ?? 0) > (row.outcomes[best] ?? 0) ? label : best
          , result.outcomeLabels[0])
          const pct = row.total > 0 ? ((row.outcomes[dominant] / row.total) * 100).toFixed(0) : '0'
          return (
            <p key={row.source} className="text-[10px] text-gray-600 truncate">
              <span className="font-medium text-gray-700">{row.source}</span>
              {' → '}{pct}% <span className="capitalize">{dominant}</span>
            </p>
          )
        })}
      </div>

      {/* Placeholder for future report */}
      <p className="text-[9px] text-gray-300 mt-2 italic">Statistical report placeholder</p>
    </div>
  )
}
