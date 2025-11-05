# Rank Simulator - AI Visibility Analyzer

Lo strumento SEO che prevede posizionamento organico e traffico potenziale, per strategie più mirate e consapevoli.

## Features

- **AI Visibility Score**: Calcola quanto il tuo contenuto è visibile alle ricerche AI
- **Query Fan-Out Simulation**: Genera query sintetiche che simulano il processo di Google AI Mode
- **Routing Format Analysis**: Identifica i formati di contenuto ottimali per ogni query
- **Actionable Recommendations**: Ricevi suggerimenti concreti per migliorare la visibilità

## Technology Stack

- **Backend**: Flask (Python)
- **AI Engine**: Google Gemini 2.5 Pro & Flash
- **Frontend**: TailwindCSS
- **Deployment**: Railway

## Installation

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Deployment

This application is configured for Railway deployment:

```bash
railway login
railway init
railway up
```

## API Keys

The application uses:
- Google Gemini API for content extraction and query generation
- Embeddings for similarity calculations

## How It Works

1. **Content Extraction**: Uses Gemini's url_context tool to extract the main entity and content chunks from the target URL
2. **Query Generation**: Generates 20+ synthetic queries with routing formats and reasoning using Gemini 2.5 Pro
3. **Coverage Analysis**: Calculates semantic similarity between queries and content using embeddings
4. **Recommendations**: Provides actionable suggestions based on coverage gaps

## License

© 2025 Rank Simulator. All rights reserved.
