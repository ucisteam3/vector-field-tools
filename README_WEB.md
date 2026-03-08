# AI Video Clipper - Web Application

A modern local web app for generating viral clips from YouTube videos using AI. Converts the Tkinter desktop app into a SaaS-style interface.

## Quick Start

### 1. Install dependencies

```bash
# Python (backend + AI modules)
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### 2. Run the app

**Terminal 1 - Backend API:**
```bash
python server.py
```
API runs at http://localhost:8000

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```
Frontend runs at http://localhost:3000

### 3. Open in browser

Go to **http://localhost:3000**

---

## Usage

1. **Dashboard**: Paste a YouTube URL and click **Analyze**
2. Analysis runs in the background (download → transcription → AI clip detection)
3. You're redirected to the **Project Editor**
4. **Video player**: Watch the full video
5. **Timeline**: Click colored segments to jump to that clip
6. **Clip list**: Each clip shows title, score, duration. Use **Play** or **Export**
7. **Export**: Generates MP4 clip with FFmpeg (saved to `projects/{id}/clips/`)
8. **Download**: After export, download the clip file

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, Python |
| Frontend | Next.js, React, TypeScript, TailwindCSS, Framer Motion |
| AI | Existing modules: ai_engine, ai_segment_analyzer, video_analyzer, clip_exporter, download_manager, transcription_engine |

---

## Project Structure

```
/
├── server.py           # Entry point: python server.py
├── backend/
│   ├── server.py       # FastAPI app
│   ├── project_manager.py
│   ├── analysis_service.py
│   ├── clip_service.py
│   └── web_context.py  # Headless adapter for AI modules
├── frontend/           # Next.js app
│   └── src/
│       ├── app/
│       │   ├── page.tsx        # Dashboard
│       │   └── project/[id]/   # Editor
│       └── lib/api.ts
├── projects/           # Saved projects (created at runtime)
│   └── {project_id}/
│       ├── video.mp4
│       ├── metadata.json
│       └── clips/
└── modules/            # Existing AI modules (unchanged)
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /analyze | Start analysis, returns `project_id` |
| GET | /projects | List all projects |
| GET | /project/{id} | Get project metadata + clips |
| GET | /project/{id}/status | Poll analysis progress |
| GET | /video/{id} | Serve source video |
| GET | /clip/{id}/{filename} | Serve clip file |
| POST | /project/{id}/export/{index} | Export single clip |

---

## Prerequisites

- **Python 3.9+** with dependencies (see requirements.txt)
- **FFmpeg** in PATH (for clip export)
- **Node.js 18+** (for frontend)
- **OpenAI API key** in `openai.txt` (for best viral detection)
- **Gemini API key** in `config.json` (optional)

---

## Local-only

All data stays on your machine. No cloud storage. Projects are saved in `projects/` and persist across sessions.
