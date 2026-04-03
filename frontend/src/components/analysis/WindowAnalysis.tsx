// @ts-ignore
import jStat from 'jStat'
import ReactMarkdown from 'react-markdown'
import { getAxisColor, rgbToHex, type GradientScheme } from '../../utils/colorBlending'
import { isOutputNode, isOutputLink, stripOutputPrefix, OUTPUT_NODE_PREFIX } from '../../constants/outputNodes'

interface SankeyNode {
  name: string
  id: string
  layer: number
  token_count: number
  label_distribution?: Record<string, number>
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
  report?: string
  selectedSchema?: string
  primaryValues?: string[]
  gradient?: GradientScheme
}

interface ContingencyResult {
  table: { source: string; outcomes: Record<string, number>; total: number }[]
  outcomeLabels: string[]
  chiSquare: number
  pValue: number
  cramersV: number
  isSignificant: boolean
  n: number
  cellResiduals: Record<string, Record<string, number>>
}

function computeContingency(nodes: SankeyNode[], links: SankeyLink[]): ContingencyResult | null {
  // Find output nodes and the links feeding into them
  const outNodes = nodes.filter(n => isOutputNode(n.name))
  if (outNodes.length < 2) return null

  const outLinks = links.filter(l => isOutputLink(l))
  if (outLinks.length === 0) return null

  // Source nodes = unique sources of output links
  const sourceNames = [...new Set(outLinks.map(l => l.source))]
  const outcomeLabels = outNodes.map(n => stripOutputPrefix(n.name))

  // Build contingency table
  const table = sourceNames.map(src => {
    const outcomes: Record<string, number> = {}
    let total = 0
    for (const label of outcomeLabels) {
      const link = outLinks.find(l => l.source === src && l.target === `${OUTPUT_NODE_PREFIX}${label}`)
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

  // Chi-square test of independence + standardized residuals for cell coloring
  let chiSquare = 0
  const r = table.length
  const c = outcomeLabels.length
  const cellResiduals: Record<string, Record<string, number>> = {}

  for (const row of table) {
    cellResiduals[row.source] = {}
    for (const label of outcomeLabels) {
      const observed = row.outcomes[label] ?? 0
      const expected = (row.total * colTotals[label]) / n
      if (expected > 0) {
        chiSquare += Math.pow(observed - expected, 2) / expected
        cellResiduals[row.source][label] = (observed - expected) / Math.sqrt(expected)
      } else {
        cellResiduals[row.source][label] = 0
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
    cellResiduals,
  }
}

function strengthLabel(v: number): string {
  if (v < 0.1) return 'negligible'
  if (v < 0.3) return 'small'
  if (v < 0.5) return 'moderate'
  return 'strong'
}

export default function WindowAnalysis({ routeData, windowLabel, report, selectedSchema, primaryValues, gradient = 'red-blue' }: WindowAnalysisProps) {
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
      <p className="text-[10px] font-semibold text-gray-700 mb-0.5">Cluster → Generated Continuation Contingency</p>
      <p className="text-[9px] text-gray-400 mb-1">
        Each row is a geometric cluster. Columns show the category of the model's generated text continuation for each probe sentence.
        Cell color: <span className="text-blue-500">blue</span> = more than expected, <span className="text-red-400">red</span> = fewer.
      </p>
      <table className="w-full text-[10px] mb-1">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left text-gray-500 py-0.5 pr-1">Cluster</th>
            <th className="text-left text-gray-500 py-0.5 px-1">Input</th>
            {result.outcomeLabels.map(label => (
              <th key={label} className="text-right text-gray-500 py-0.5 px-1 capitalize">{label}</th>
            ))}
            <th className="text-right text-gray-400 py-0.5 pl-1">n</th>
          </tr>
        </thead>
        <tbody>
          {result.table.map(row => {
            // Look up the source node to get its input label distribution
            const sourceNode = routeData?.nodes.find(n => n.name === row.source)
            const labelDist = sourceNode?.label_distribution
            let dominantInput = ''
            let dominantPct = 0
            let dominantColor = '#808080'
            if (labelDist) {
              const total = Object.values(labelDist).reduce((s, v) => s + v, 0)
              const sorted = Object.entries(labelDist).sort((a, b) => b[1] - a[1])
              if (sorted.length > 0 && total > 0) {
                dominantInput = sorted[0][0]
                dominantPct = Math.round((sorted[0][1] / total) * 100)
                if (primaryValues && primaryValues.length > 0) {
                  dominantColor = rgbToHex(getAxisColor(dominantInput, primaryValues, gradient))
                }
              }
            }
            return (
              <tr key={row.source} className="border-b border-gray-100">
                <td className="text-gray-700 font-medium py-0.5 pr-1 truncate max-w-[60px]">{row.source}</td>
                <td className="py-0.5 px-1">
                  {dominantInput ? (
                    <span className="inline-flex items-center gap-0.5">
                      <span className="inline-block w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: dominantColor }} />
                      <span className="text-gray-700 capitalize truncate max-w-[50px]">{dominantInput}</span>
                      <span className="text-gray-400">{dominantPct}%</span>
                    </span>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
                {result.outcomeLabels.map(label => {
                  const val = row.outcomes[label] ?? 0
                  const pct = row.total > 0 ? ((val / row.total) * 100).toFixed(0) : '0'
                  const pctNum = row.total > 0 ? val / row.total : 0
                  const expected = 1 / result.outcomeLabels.length
                  const deviation = pctNum - expected
                  const intensity = Math.min(Math.abs(deviation) / (1 - expected), 1)
                  const bgColor = deviation >= 0
                    ? `rgba(59, 130, 246, ${intensity * 0.75})`
                    : `rgba(239, 68, 68, ${intensity * 0.75})`
                  return (
                    <td key={label} className="text-right text-gray-800 py-0.5 px-1" style={{ backgroundColor: bgColor }}>
                      {val} <span className="text-gray-400">({pct}%)</span>
                    </td>
                  )
                })}
                <td className="text-right text-gray-400 py-0.5 pl-1">{row.total}</td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {/* Stats */}
      <div className="mt-1.5 pt-1.5 border-t border-gray-100 max-w-[220px] space-y-0.5 text-[10px]">
        <div className="flex justify-between gap-x-3">
          <span className="text-gray-500">χ²({(result.table.length - 1) * (result.outcomeLabels.length - 1)})</span>
          <span className="font-mono text-gray-800">{result.chiSquare.toFixed(2)}</span>
        </div>
        <div className="flex justify-between gap-x-3">
          <span className="text-gray-500">p-value</span>
          <span className={`font-mono ${result.isSignificant ? 'text-green-700 font-semibold' : 'text-gray-800'}`}>
            {result.pValue < 0.001 ? '<0.001' : result.pValue.toFixed(4)}
          </span>
        </div>
        <div className="flex justify-between gap-x-3">
          <span className="text-gray-500">Cramer's V</span>
          <span className="font-mono text-gray-800">{result.cramersV.toFixed(3)} ({strengthLabel(result.cramersV)})</span>
        </div>
        <div className="flex justify-between gap-x-3">
          <span className="text-gray-500">Significant</span>
          <span className={`font-semibold ${result.isSignificant ? 'text-green-600' : 'text-red-500'}`}>
            {result.isSignificant ? 'Yes' : 'No'}
          </span>
        </div>
      </div>

      {/* AI Analysis Report */}
      {report ? (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <p className="text-[10px] font-semibold text-gray-600 mb-1">AI Analysis</p>
          <div className="prose prose-sm max-w-none text-[10px] text-gray-700 max-h-[300px] overflow-y-auto">
            <ReactMarkdown>{report}</ReactMarkdown>
          </div>
        </div>
      ) : selectedSchema ? (
        <p className="text-[9px] text-gray-400 mt-2 italic">
          No report for this window. Use /analyze to generate one.
        </p>
      ) : null}
    </div>
  )
}
