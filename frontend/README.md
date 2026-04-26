# Open LLMRI — Frontend

React + Vite + TypeScript visualization for MoE routing patterns and latent
trajectories. The canonical UI is `MUDApp.tsx`, served at `/`.

## Layout

```
src/
├── pages/
│   └── MUDApp.tsx                       # Canonical UI: toolbar + analysis grid + MUD terminal
├── components/
│   ├── toolbar/Toolbar.tsx              # Session/schema/axis controls + SchemaSummary
│   ├── charts/
│   │   ├── SankeyChart.tsx              # ECharts Sankey (single transition)
│   │   ├── MultiSankeyView.tsx          # 6-transition window orchestrator
│   │   └── SteppedTrajectoryPlot.tsx    # Three.js 3D stepped UMAP trajectory
│   ├── analysis/
│   │   ├── ExpertRoutesSection.tsx      # Expert routing panel
│   │   ├── ClusterRoutesSection.tsx     # Cluster routing panel
│   │   ├── TemporalAnalysisSection.tsx  # Temporal lag plots
│   │   ├── WindowAnalysis.tsx           # Per-window written report viewer
│   │   ├── ContextSensitiveCard.tsx     # Click-to-inspect node/route card
│   │   └── SchemaSummary.tsx            # Natural-language schema paragraph (rendered in Toolbar)
│   └── terminal/MUDTerminal.tsx         # Embedded Evennia client
├── hooks/
│   ├── useAxisControls.ts               # Color/blend/shape axis state
│   └── useSchemaManagement.ts           # Schema list + selection + reports cache
├── api/client.ts                        # Typed API client
├── types/api.ts                         # TypeScript interfaces matching backend responses
├── utils/colorBlending.ts               # Gradients + categorical palettes
└── constants/layerWindows.ts            # The 4 fixed windows (w0–w3) and their transitions
```

## Running

```bash
npm install
npm run dev    # http://localhost:5173
```

Backend expected at `http://localhost:8000/api`.

WSL2 note: `vite.config.ts` enables `usePolling: true` for file watching on
NTFS — HMR works on the Windows filesystem out of the box.

## Architecture conventions

- The right column of every Sankey is fixed at build time as **friend / foe /
  unknown** (driven by `ground_truth`). Color-axis dropdown changes paint
  these existing nodes locally — no refetch.
- `output_grouping_axes` is no longer a runtime parameter; the request field
  is ignored if sent.
- A schema covers all 4 fixed windows × 6 transitions × {cluster + 3 expert
  ranks}. Per-window reports populate `WindowAnalysis` automatically.
