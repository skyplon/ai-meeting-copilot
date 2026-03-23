# AI Meeting Co-pilot

> Agentic AI app that turns a meeting transcript or audio file into a structured summary, action items routed to Jira/Asana/Linear, a follow-up calendar event, and an HTML summary email — all in ~30 seconds.

Built as a PM portfolio project to demonstrate **Agentic AI** and **Generative AI** engineering skills.

![Input Screen](https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%201.png?raw=true)

---

## How it works

**Input:** paste a transcript or upload an audio file (.mp3, .m4a, .wav)

**Output in ~30 seconds:**

| Tab | What you get |
|---|---|
| Summary | Meeting goal, decisions made, open blockers, mood |
| Action items | Tasks extracted via Claude tool use, routed to Jira / Asana / Linear |
| Transcript | Speaker-labeled turns with timestamps |
| Email draft | Formatted HTML email ready to send to all attendees |
| Slack brief | Markdown brief with priority emojis and @mentions |

---

## Screenshots

### Agent pipeline — 7 nodes running in sequence

![Processing Pipeline](https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%202.png?raw=true)

### Results overview — stat cards and follow-up banner

![Results Overview](https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%203.png?raw=true)

### Summary tab — goal, decisions, and open blockers

![Summary Tab](https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%204.png?raw=true)

### Action items — routed to Jira, Asana, and Linear automatically

![Action Items](https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%205.png?raw=true)

### Transcript tab — speaker-labeled turns with timestamps

![Transcript](https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%206.png?raw=true)

### Email draft — full HTML summary ready to send

![Email Draft](https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%207.png?raw=true)

### Audio upload — drag and drop .mp3, .m4a, .wav files

![Audio Upload](https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%208.png?raw=true)

### Audio results — full pipeline output from real audio

![Audio Results](https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%209.png?raw=true)

---

## Architecture

7 LangGraph agents run in sequence. Each node is a specialized AI agent with a defined role, input/output contract, and tool access.

```
Audio / Text input
       │
       ▼
┌─────────────────────┐
│  TranscriptionAgent │  OpenAI Whisper → diarized transcript
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│    SummaryAgent     │  Claude + Instructor → typed MeetingSummary
└──────────┬──────────┘
           │
┌──────────▼──────────────┐
│  ActionExtractorAgent   │  Claude tool use → agentic extraction loop
└──────────┬──────────────┘
           │
┌──────────▼──────────┐
│    RouterAgent      │  claude-haiku classifier → Jira / Asana / Linear
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│    MemoryAgent      │  Pinecone vector search → recurring issue detection
└──────────┬──────────┘
           │
    follow_up_needed?
     yes ──► SchedulerAgent    Google Calendar MCP
     no  ──► DistributionAgent
           │
┌──────────▼──────────┐
│  DistributionAgent  │  HTML email + Slack brief generator
└──────────┬──────────┘
           │
          END
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| LLM backbone | claude-3-7-sonnet, claude-haiku-4-5 | All reasoning agents |
| Agent orchestration | LangGraph 0.2+ | Stateful graph, conditional edges, checkpointing |
| LLM framework | LangChain 0.3+ | Prompt templates, LCEL chains |
| Structured output | Instructor + Pydantic v2 | Zero untyped LLM responses |
| Speech-to-text | OpenAI Whisper | Audio transcription |
| Embeddings | text-embedding-3-small | Semantic memory vectors |
| Vector DB | Pinecone (or in-memory mock) | Episodic memory for recurring issues |
| MCP servers | Google Calendar, Gmail, Jira, Asana | Real-world agentic integrations |
| Backend | FastAPI + Uvicorn | REST API, file upload, background jobs |
| Frontend | React 18 + Vite | Upload UI, pipeline view, results dashboard |

---

## AI Skills Demonstrated

| Skill | Where in the code |
|---|---|
| **LangGraph** — stateful multi-agent graph | `backend/graph/graph.py` — 7 nodes, conditional edges |
| **Claude tool use** — agentic loop | `backend/agents/action_extractor.py` — iterates until extraction complete |
| **Structured outputs** — Instructor + Pydantic | `backend/agents/summary.py` — every LLM call returns a typed schema |
| **RAG + embeddings** | `backend/agents/memory.py` — embed blockers, cosine similarity search |
| **Memory systems** | 3-tier: working state / Redis-ready / Pinecone episodic |
| **MCP integrations** | `backend/agents/router.py`, `scheduler.py` — Calendar, Gmail, Jira, Asana |
| **Prompt engineering** | XML-structured prompts, few-shot examples, persona grounding |
| **Batch processing** | Background job queue for audio uploads with polling |

---

## Project Structure

```
ai-meeting-copilot/
├── backend/
│   ├── agents/
│   │   ├── transcription.py    Whisper API + speaker turn detection
│   │   ├── summary.py          Claude + Instructor → MeetingSummary
│   │   ├── action_extractor.py Claude tool use extraction loop
│   │   ├── router.py           claude-haiku classifier + task routing
│   │   ├── scheduler.py        Calendar event generation
│   │   ├── memory.py           Pinecone / mock recurring issue detection
│   │   └── distribution.py     HTML email + Slack brief
│   ├── graph/
│   │   └── graph.py            LangGraph StateGraph — 7 nodes, conditional edges
│   ├── models/
│   │   └── schemas.py          All Pydantic models + MeetingState
│   ├── api/
│   │   └── main.py             FastAPI endpoints
│   ├── tests/
│   │   └── test_agents.py      18 unit tests + integration test
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   └── components/
    │       ├── InputPanel.jsx       Transcript input + audio upload
    │       ├── ProcessingView.jsx   Animated agent pipeline
    │       └── ResultsView.jsx      Results dashboard
    └── vite.config.js
```

---

## Setup

### Requirements

- Python 3.11+
- Node 18+
- Anthropic API key — [console.anthropic.com](https://console.anthropic.com)
- OpenAI API key — [platform.openai.com](https://platform.openai.com)

### 1. Clone and configure

```bash
git clone https://github.com/skyplon/ai-meeting-copilot.git
cd ai-meeting-copilot/backend
cp .env.example .env
# Add your ANTHROPIC_API_KEY and OPENAI_API_KEY to .env
```

### 2. Install backend

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Start the backend

```bash
# Always run from the project root
cd ~/ai-meeting-copilot
uvicorn backend.api.main:app --reload --port 8000
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and click **Load demo transcript** to test immediately.

### Quick API test (no UI needed)

```bash
curl -X POST http://localhost:8000/api/meetings/process-text \
  -H "Content-Type: application/json" \
  -d '{
    "transcript_text": "Alice: Fix the login bug by Friday, blocking customers.\nBob: On it. Carlos can you review my PR?\nCarlos: Yes, tag me.\nAlice: Also decided to delay the dashboard to Q3.",
    "meeting_title": "Sprint Planning",
    "attendees": ["alice@co.com", "bob@co.com", "carlos@co.com"]
  }'
```

---

## Optional Upgrades

### Pinecone — real recurring issue detection

```bash
# Add to backend/.env
PINECONE_API_KEY=your-key
PINECONE_INDEX_NAME=meeting-memory
```

Create a free index at [pinecone.io](https://pinecone.io) with dimension `1536`, metric `cosine`. Run two meetings with the same blocker — the amber recurring issue banner fires automatically on the second run.

### LangSmith — full agent observability

```bash
# Add to backend/.env
LANGSMITH_API_KEY=your-key
LANGCHAIN_TRACING_V2=true
LANGSMITH_PROJECT=ai-meeting-copilot
```

Every agent run is traced at [smith.langchain.com](https://smith.langchain.com) — token cost per node, latency, and full prompt/response for every Claude call.

---

## Running Tests

```bash
# Unit tests only — no API calls, runs instantly
pytest backend/tests/ -v -m unit

# Full integration test including real Claude API (~$0.01)
pytest backend/tests/ -v
```

---

## Technical Specification

See the full product spec in [`AI_Meeting_Copilot_TechSpec.docx`](./docs/AI_Meeting_Copilot_TechSpec.docx) — agent architecture, data flow diagrams, memory system design, RAG pipeline configuration, and API integration details.

---

*Built by Juan Navarrete — PM portfolio project showcasing Agentic AI and Generative AI engineering skills.*
