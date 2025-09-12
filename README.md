# Concept MRI - OpenAI Hackathon 2025

## Interpretability for Mixture of Experts Models through Concept Trajectory Analysis

Concept MRI applies advanced interpretability techniques to understand how Mixture of Experts (MoE) models process information. By analyzing expert routing patterns and latent representations, we provide unprecedented visibility into the decision pathways within these complex architectures.

## Quick Setup for Judges

### Prerequisites
- Python 3.11+
- Node.js 18+
- CUDA-capable GPU (optional but recommended)
- 8GB+ RAM minimum

### Installation and Setup

```bash
# 1. Clone and setup everything
git clone https://github.com/AndrewSmigaj/OpenAIHackathon-ConceptMRI.git
cd OpenAIHackathon-ConceptMRI
make setup    # Installs all dependencies

# 2. Add your API keys to .env file
cp .env.example .env
nano .env     # Add OPENAI_API_KEY and/or ANTHROPIC_API_KEY

# 3. Run the application (use 2 terminals)
# Terminal 1: Backend
make run-api  # Starts backend on port 8000

# Terminal 2: Frontend  
make run-ui   # Starts frontend on port 5173
```

### Access the Application
- **Frontend UI**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs

## Demo Example - Sentiment Analysis with Positive/Negative Nouns and Verbs

⚠️ **Important Note**: Currently, the system only supports specific pre-defined category axes for analysis:
- **Sentiment**: positive/negative
- **Parts of Speech**: nouns/verbs
- **Concreteness**: concrete/abstract
- **Temporal**: temporal words
- **Cognitive**: cognitive words

Custom categories and axes are a planned future feature. For now, please use the provided demo categories or run the comprehensive probe script (see below).

### Create a Probe Session
```python
POST /api/probes
{
  "session_name": "Sentiment Analysis Demo",
  "context_sources": [
    {"source_type": "custom", "source_params": {"words": ["the"], "label": "determiner"}}
  ],
  "target_sources": [
    {"source_type": "custom", "source_params": {
      "words": ["hero", "friend", "joy", "peace"],
      "label": "positive_nouns"
    }},
    {"source_type": "custom", "source_params": {
      "words": ["love", "help", "save", "build"],
      "label": "positive_verbs"
    }},
    {"source_type": "custom", "source_params": {
      "words": ["villain", "enemy", "pain", "war"],
      "label": "negative_nouns"  
    }},
    {"source_type": "custom", "source_params": {
      "words": ["hate", "hurt", "destroy", "break"],
      "label": "negative_verbs"  
    }}
  ]
}
```

### Execute the Probe
```python
POST /api/probes/{session_id}/execute
```

### Run an Experiment
```python
POST /api/experiments/create
{
  "probe_ids": ["probe_123"],
  "word_lists": {
    "positive_nouns": ["hero", "friend", "joy", "peace"],
    "positive_verbs": ["love", "help", "save", "build"],
    "negative_nouns": ["villain", "enemy", "pain", "war"],
    "negative_verbs": ["hate", "hurt", "destroy", "break"]
  }
}
```

### View Results
```python
GET /api/experiments/{experiment_id}/results
```

## Populating the Full Dataset (Recommended)

To reproduce the comprehensive dataset we used for development with thousands of words across multiple categories:

```bash
# Make sure backend is running first (make run-api)
cd scripts
python3 create_massive_comprehensive_probe.py
```

This will create probe sessions with:
- 2 context words (determiners: "the", "a")  
- 1000+ target words across all supported categories
- Categories include: positive/negative nouns, positive/negative verbs, concrete/abstract, temporal, cognitive, and more

The script will automatically execute the probes and populate your data lake with the same comprehensive dataset we used.

## Features

- **Expert Highway Analysis**: Visualize how tokens flow through different experts across layers
- **Latent Space Exploration**: Analyze PCA-reduced representations to understand conceptual trajectories
- **Clustering & Categorization**: Automatic grouping of similar routing patterns and semantic concepts
- **Interactive Visualizations**: Real-time Sankey diagrams showing token flow through the model

## Technical Details

- **Model**: GPT-OSS-20B with 4-bit quantization (NF4)
- **Storage**: Parquet-based data lake
- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI + Python

## Troubleshooting

### Common Issues

1. **CUDA Out of Memory**: Add `DEVICE=cpu` to your .env file
2. **Missing WordNet Data**: Run `python -c "import nltk; nltk.download('wordnet')"`
3. **Port Conflicts**: Check if ports 8000 or 5173 are in use

### Manual Commands (if Make doesn't work)

```bash
# Backend (Terminal 1)
cd backend/src
python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (Terminal 2)
cd frontend
npm install
npm run dev
```

## Project Structure

```
OpenAIHackathon-ConceptMRI/
├── backend/src/           # Python FastAPI backend
├── frontend/src/          # React frontend
├── data/                  # Parquet storage
├── Makefile              # Setup and run commands
└── README.md             # This file
```