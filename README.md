# PSG Rostering Tool

This repository now includes a holographic-inspired command center for interacting with the PSG rostering engine.

## Backend API

The API is implemented with [FastAPI](https://fastapi.tiangolo.com/) in `src/api/server.py` and exposes:

- `POST /api/solve`: Accepts mission criteria (slider + toggle payloads) and returns an aggregated schedule response.
- `WS /ws/roster`: Provides live updates when criteria messages are pushed over a WebSocket connection.

Run the API with:

```bash
pip install -r requirements.txt
uvicorn src.api.server:app --reload
```

The service will use OR-Tools if it is available, but automatically falls back to a deterministic mock schedule when the solver is not installed.

## Frontend Command Center

A Next.js + Tailwind CSS frontend lives under `frontend/` and renders the Jarvis-style control room with animated timeline, KPI deck, and scenario comparison widgets.

Install dependencies and start the development server with:

```bash
cd frontend
npm install
npm run dev
```

The UI connects to the backend via WebSocket (`NEXT_PUBLIC_ROSTER_WS`) with a REST fallback (`NEXT_PUBLIC_ROSTER_REST`) and streams schedule updates into the visualization.
