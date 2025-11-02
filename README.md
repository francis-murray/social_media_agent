# Social Media Content Generator

## Overview

An AI‑powered tool that generates high‑quality, platform‑specific social posts from YouTube videos. An agent orchestrates the end‑to‑end workflow—from transcript retrieval to content generation. Built with Next.js (frontend) and FastAPI (backend).

## How to Run

### 1. Start the Backend

```bash
cd backend

# Ensure .env contains OPENAI_API_KEY
uv run fastapi dev server.py
```

Backend runs at `http://localhost:8000`.

### 2. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

## How to Use

1. Open `http://localhost:3000`.
2. Enter a YouTube video URL or ID.
3. Select platforms to generate content for.
4. Click "Generate Content" (you’ll see progress and results).

## API Endpoints

### GET `/`
Returns API information and available endpoints.

### GET `/health`
Checks API health and OpenAI key configuration.

### POST `/generate`
Generates social media content from a YouTube video.

Request body:
```json
{
  "video_id": "LCEmiRjPEtQ",
  "platforms": ["LinkedIn", "Instagram"]
}
```

Response:
```json
{
  "video_id": "LCEmiRjPEtQ",
  "posts": [
    { "platform": "LinkedIn", "content": "..." },
    { "platform": "Instagram", "content": "..." }
  ],
  "transcript_preview": "First 200 chars of transcript..."
}
```

Note on usage:
- This endpoint is not called by the frontend. It exists for scripts, CLI/testing via curl, Swagger UI, and backend‑to‑backend integrations that want a single final response without streaming.

### GET `/generate/stream`
Server‑Sent Events (SSE) endpoint that streams progress while generating content.

Query params:
- `video_id` (string, required)
- `platforms` (string[], repeatable, optional; defaults to ["LinkedIn","Instagram"]) — e.g. `...&platforms=LinkedIn&platforms=Instagram`
- `language` (string, optional; defaults to `en`)

Event types emitted:
- `status`: `{ "stage": "starting" | "transcript_ready" | "generating" | "done", "platform"?, "index"? }`
- `transcript`: `{ "preview": string, "length": number }`
- `post`: `{ "platform": string, "content": string }`
- `error`: `{ "message": string }`
- `done`: `{}`

Example (browser):
```javascript
const params = new URLSearchParams();
params.append("video_id", "LCEmiRjPEtQ");
params.append("platforms", "LinkedIn");
params.append("platforms", "Instagram");
params.append("language", "en");
const es = new EventSource(`http://localhost:8000/generate/stream?${params.toString()}`);

es.addEventListener("status", e => console.log("status", JSON.parse(e.data)));
es.addEventListener("transcript", e => console.log("transcript", JSON.parse(e.data)));
es.addEventListener("post", e => console.log("post", JSON.parse(e.data)));
es.addEventListener("error", e => console.error("error", e));
es.addEventListener("done", () => es.close());
```

Note on usage:
- Why GET method? SSE (EventSource) in browsers only supports GET. 
- The request data (video_id, platforms, language) is sent as query parameters. 

### GET `/transcript`
Returns the full transcript text for a video.

Query params:
- `video_id` (string, required)
- `language` (string, optional; defaults to `en`)
- `refresh` (boolean, optional; default `false`) — bypass cache and refetch

Response:
```json
{
  "video_id": "LCEmiRjPEtQ",
  "language": "en",
  "transcript": "full transcript text...",
  "length": 12345
}
```

Note on caching:
- Transcripts are served from an in‑memory cache keyed by `(video_id, language)` with a short TTL to avoid repeated fetches.


## Testing the API

Using curl:
```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "LCEmiRjPEtQ",
    "platforms": ["LinkedIn", "Instagram"],
    "language": "en"
  }'
```

Swagger UI: `http://localhost:8000/docs`

## Architecture

```
Frontend (Next.js/React)
    ↓ HTTP POST
Backend (FastAPI)
    ↓ Calls
YouTube Transcript API
    ↓ Returns transcript
OpenAI Agents (via agents library)
    ↓ Generates
Social Media Content
    ↓ Returns
Frontend displays results
```

## Features

### Frontend
- Modern UI with dark mode
- Responsive layout
- Platform selection and live progress
- One‑click copy

### Backend
- FastAPI with async processing
- Automatic API docs
- Request/response validation
- Error handling and logging

## Notes

- Generation typically takes 10–30 seconds depending on transcript length.
- Ensure your OpenAI API key has sufficient credits.
- CORS is permissive for local dev; harden for production.

## Troubleshooting

- Failed to fetch: ensure backend is running at `http://localhost:8000`.
- OPENAI_API_KEY is not set: add it to `backend/.env`.
- CORS errors: adjust `allow_origins` in `backend/api/server.py`.
