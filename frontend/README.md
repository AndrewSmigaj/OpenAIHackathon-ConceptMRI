# Concept MRI — Frontend

React visualization for MoE routing patterns and latent trajectories.

## Architecture

```
src/
├── pages/
│   ├── ExperimentPage.tsx       # Main analysis page (session, routing, clustering, inspection)
│   └── WorkspacePage.tsx        # Session list and selection
├── components/
│   ├── charts/
│   │   ├── SankeyChart.tsx      # ECharts Sankey diagram (single window)
│   │   ├── MultiSankeyView.tsx  # Multi-window Sankey orchestrator (6 windows + output)
│   │   └── SteppedTrajectoryPlot.tsx  # Three.js 3D stepped trajectory visualization
│   └── analysis/
│       ├── WindowAnalysis.tsx         # Chi-square statistics panel per window
│       ├── ContextSensitiveCard.tsx   # Click-to-inspect card (cluster/route details)
│       ├── LLMAnalysisPanel.tsx       # AI analysis with scaffold templates
│       ├── ExpertRoutesSection.tsx    # Expert routing view wrapper
│       └── ClusterRoutesSection.tsx   # Cluster routing view wrapper
├── api/
│   └── client.ts           # Typed API client for all backend endpoints
├── utils/
│   └── colorBlending.ts    # Color system: gradients, categorical palettes, traffic scaling
├── types/
│   └── api.ts              # TypeScript interfaces matching backend responses
└── constants/
    └── colors.ts            # Color scheme definitions
```

## Key Features

- **Multi-window Sankey diagrams**: 6 consecutive layer transitions + output nodes, colored by any detected axis
- **3D stepped trajectory plots**: UMAP-reduced latent representations with per-label coloring
- **Click-to-inspect cards**: Select any cluster or route to see label distributions, example sentences, and AI descriptions
- **Chi-square analysis**: Per-window contingency tables with standardized residuals
- **Dynamic axis detection**: Color axes auto-detected from session data (label, categories, target word)

## Running

```bash
npm install
npm run dev    # http://localhost:5173
```

Expects backend at `http://localhost:8000/api` (hardcoded in `api/client.ts`).

WSL2 note: `vite.config.ts` has `usePolling: true` for file watching on Windows filesystem.
