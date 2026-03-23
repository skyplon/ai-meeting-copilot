# AI Meeting Co-pilot

> Agentic AI system that turns a meeting transcript into action items, routed tasks, a follow-up calendar event, and a summary email — automatically.

**Portfolio project demonstrating:** LangGraph · Claude API (tool use + structured output) · RAG + Embeddings · Memory systems · MCP server integrations · Whisper transcription

---

## Demo

1. Paste a transcript (or upload audio)
2. Watch 7 agents run in sequence through the LangGraph pipeline
3. Get: structured summary · action items routed to Jira/Asana · follow-up meeting scheduled · HTML email ready to send

---

## Architecture

```
Audio / Text
     │
     ▼
┌────────────────────┐
│ TranscriptionAgent │  Whisper large-v3 + pyannote diarization
└─────────┬──────────┘
          │
┌─────────▼──────────┐
│    SummaryAgent    │  claude-3-5-haiku + Instructor → MeetingSummary (Pydantic)
└─────────┬──────────┘
          │
┌─────────▼──────────────┐
│ ActionExtractorAgent   │  Claude tool use — agentic extraction loop
└──────┬─────────────────┘
       │         │
  ┌────▼───┐ ┌───▼────────┐   ← parallel fan-out (LangGraph)
  │ Router │ │   Memory   │
  │ Agent  │ │   Agent    │   Memory: Pinecone vector store OR in-memory mock
  └────┬───┘ └───┬────────┘
       └────┬────┘           ← fan-in join
            │
   follow_up_needed?
     yes ──►SchedulerAgent   Google Calendar MCP
     no  ──►DistributionAgent
            │
   DistributionAgent         Gmail MCP + Slack Bolt SDK
            │
           END
```

## Tech Stack

| Layer | Technology |
|---|---|
| LLM backbone | `claude-3-7-sonnet`, `claude-haiku-4-5` |
| Orchestration | LangGraph 0.2+ (StateGraph, checkpointing) |
| LLM framework | LangChain 0.3+ (LCEL, prompt templates) |
| Structured output | Instructor + Pydantic v2 |
| Embeddings | `text-embedding-3-small` (OpenAI) |
| Vector DB | Pinecone serverless (or in-memory mock) |
| Speech-to-text | OpenAI Whisper API |
| MCP servers | Google Calendar, Gmail, Jira, Asana |
| Observability | LangSmith |
| Backend | FastAPI + Uvicorn |
| Frontend | React 18 + Vite |

---

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/your-username/ai-meeting-copilot
cd ai-meeting-copilot/backend
cp .env.example .env
```

Edit `.env` — at minimum you need:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### 2. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Start the backend

```bash
uvicorn api.main:app --reload --port 8000
```

The API is now running at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### 4. Install and start the frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open `http://localhost:5173` — the full UI is ready.

---

## Quick API test (no frontend needed)

```bash
curl -X POST http://localhost:8000/api/meetings/process-text \
  -H "Content-Type: application/json" \
  -d '{
    "transcript_text": "Alice: We need to fix the login bug by Friday.\nBob: I will handle that. Should take a day.\nAlice: Also, we have decided to delay the dashboard to Q3.\nBob: Got it. I will file a Jira ticket for the bug and update the roadmap.",
    "meeting_title": "Sprint Planning",
    "attendees": ["alice@company.com", "bob@company.com"]
  }'
```

---

## Running tests

```bash
# Unit tests only (no API calls, fast)
pytest tests/ -v -m unit

# All tests including real Claude API calls (~$0.01)
pytest tests/ -v
```

---

## Enable Pinecone (optional — recurring issue detection)

1. Create a free Pinecone account at [pinecone.io](https://pinecone.io)
2. Create an index named `meeting-memory` with dimension `1536`, metric `cosine`
3. Add to `.env`:
   ```
   PINECONE_API_KEY=your-key
   PINECONE_INDEX_NAME=meeting-memory
   ```

Without Pinecone, the system uses an in-memory mock store that works for the current session.

---

## Enable LangSmith (optional — observability)

```
LANGSMITH_API_KEY=your-key
LANGSMITH_PROJECT=ai-meeting-copilot
LANGCHAIN_TRACING_V2=true
```

Every agent run will be traced at [smith.langchain.com](https://smith.langchain.com) — you can see token usage per node, latency, and full input/output for every LangGraph step.

---

## Project structure

```
ai-meeting-copilot/
├── backend/
│   ├── agents/
│   │   ├── transcription.py    Whisper + text parser
│   │   ├── summary.py          Claude + Instructor → structured summary
│   │   ├── action_extractor.py Claude tool use extraction loop
│   │   ├── router.py           claude-haiku classifier + task creation
│   │   ├── scheduler.py        Calendar event generation
│   │   ├── memory.py           Pinecone / mock recurring issue detection
│   │   └── distribution.py     HTML email + Slack brief
│   ├── graph/
│   │   └── graph.py            LangGraph StateGraph definition
│   ├── models/
│   │   └── schemas.py          All Pydantic models + MeetingState
│   ├── api/
│   │   └── main.py             FastAPI endpoints
│   ├── tests/
│   │   └── test_agents.py      Unit + integration tests
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx             Main app + API calls
    │   └── components/
    │       ├── InputPanel.jsx  Transcript input + audio upload
    │       ├── ProcessingView.jsx  Animated pipeline progress
    │       └── ResultsView.jsx Full results dashboard
    ├── index.html
    └── vite.config.js
```

---

## Skills demonstrated

| Skill | Where |
|---|---|
| **LangGraph** — stateful multi-agent graph | `graph/graph.py` — 7 nodes, conditional edges, parallel fan-out |
| **Claude tool use** — agentic loop | `agents/action_extractor.py` — iterative tool calling until complete |
| **Structured outputs** — Instructor + Pydantic | `agents/summary.py`, `agents/scheduler.py` — zero untyped LLM responses |
| **RAG + embeddings** | `agents/memory.py` — embed blockers, Pinecone similarity search |
| **Memory systems** | 3-tier: working (state), short-term (Redis-ready), long-term (Pinecone) |
| **MCP servers** | `agents/router.py`, `agents/scheduler.py` — Calendar + Gmail + Jira + Asana |
| **Prompt engineering** | XML-structured prompts, few-shot examples, persona-grounded system prompts |
| **Observability** | LangSmith tracing — token cost + latency per node |
| **FastAPI** | Full REST API with background tasks, file upload, polling |
| **React** | Functional components, hooks, async state, polling pattern |

---

## Technical specification

See [`AI_Meeting_Copilot_TechSpec.docx`](./docs/AI_Meeting_Copilot_TechSpec.docx) for the full product spec including agent architecture diagrams, data flow, memory system design, and API integration details.
