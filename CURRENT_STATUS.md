# Current Status - OpenAI Hackathon Concept MRI

## Critical Blocker: Modal Positioning Issue
**NewProbeDialog modal appears off-screen, cut-off, too small** - prevents testing probe creation flow. User criticized "program by coincidence" CSS attempts. Need simple positioning fix.

## What's Working
- ✅ Backend server running on port 8000 with GPT-OSS-20B loaded successfully
- ✅ Frontend dev server on port 5173 
- ✅ WorkspacePage with integrated NewProbeDialog component
- ✅ Complete probe creation wizard implemented (800+ lines)
- ✅ TypeScript API interfaces fixed (pos_tag→pos, synset_name→synset_id)
- ✅ Old probe sessions archived to /archive/

## Probe Creation Implementation Status
**NewProbeDialog.tsx** - COMPLETE but blocked by modal positioning:
- Multi-step wizard: config → sources → review → confirm → executing  
- Three demo presets matching architecture.yaml
- Two-phase execution (create → show counts → execute)
- WordNet integration (synsets, hyponyms, POS-pure)
- Form validation and error handling

## Key Technical Understanding
- **Probe Sessions** vs **Experiments** are separate workflows
- Experiments SELECT probe sessions to analyze (not single lens)
- MoE capture → Parquet storage → Expert/Latent analysis
- Demo flow: POS contrast, semantic categories, context disambiguation
- Two analysis tabs: Expert Highways (Sankey) + Latent Space (3D PCA)

## Files Modified
- `frontend/src/types/api.ts` - Fixed critical interface bugs
- `frontend/src/components/NewProbeDialog.tsx` - Complete implementation  
- `frontend/src/pages/WorkspacePage.tsx` - Integrated dialog
- `frontend/src/components/Modal.tsx` - Broken positioning needs fix

## Immediate Next Steps
1. **FIX MODAL POSITIONING** - simple CSS solution (mx-auto + mt-8)
2. Test end-to-end probe creation once modal works
3. Restructure UI: grid layout → sidebar + main panel design  
4. Build ExperimentPage with 2-tab analysis interface
5. Design experiment data API endpoints for Parquet reading

## UI Design Direction  
- Desktop-focused hackathon MVP
- Sidebar navigation (not grid cards)
- Separate probe creation from experiment analysis
- Clean demo recording experience

## Demo Scenarios Ready
1. **POS Contrast**: determiner context → noun/verb targets
2. **Semantic Categories**: WordNet synset hyponyms analysis  
3. **Context Disambiguation**: same word, different contexts

## Context: This is day X of 7-day hackathon. Primary goal is working probe→experiment demo flow for video recording.