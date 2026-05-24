# AI Meeting Co-pilot

**An agentic AI system that transforms a meeting transcript or audio file into structured action items, routed tasks, a follow-up calendar event, and a formatted summary email — automatically, in under 60 seconds.**

**🟢 Live demo: [ai-meeting-copilot-ten.vercel.app](https://ai-meeting-copilot-ten.vercel.app)**

---

## The Problem

Knowledge workers spend 30–40% of their working week in meetings. The cost is not the meeting itself — it is the broken operations around it.

Action items get missed because they were never written down. Decisions go undocumented and get relitigated two weeks later. Follow-up falls through because no one owns the scheduling. Context is lost between sessions because there is no persistent memory of what was raised and when.

Existing tools stop at transcription and summarization. They produce a document that someone still has to read, parse, and act on. The last mile — routing tasks to the right tool, scheduling the follow-up, detecting recurring blockers, distributing the brief — remains entirely manual.

This system closes that loop. It does not just record what happened in a meeting. It does the operational work that should happen after every meeting, and that almost never does.

---

## Who It's For

**Product Managers** running sprint planning, roadmap reviews, and cross-functional syncs. They lose the most time to poor meeting ops — action items routed to the wrong tool, follow-ups never scheduled, and the same blockers raised in every meeting because nobody tracked them.

**Engineering Leads** who need a clean, timestamped record of decisions and technical commitments made in planning sessions — without spending 20 minutes writing it up.

**Team Leads and Chiefs of Staff** who manage high-meeting-volume schedules and need automated distribution of meeting summaries across Slack and email without manual drafting.

**Operations and EA roles** who own the logistics of team meetings and need follow-up events created, attendees notified, and action items tracked without touching four different tools.

---

## What It Produces

Given a transcript (pasted text or uploaded audio), the system runs a 7-agent pipeline and outputs:

| Output | Description |
|---|---|
| Structured summary | Meeting goal, decisions made, open blockers, mood classification |
| Action items | Every task extracted via Claude tool use — with owner, due date, and priority |
| Routed tasks | Each action item sent to Jira, Asana, Linear, or Notion based on type |
| Follow-up event | Calendar invite auto-created for any unresolved blockers |
| HTML email | Formatted summary email ready to send to all attendees |
| Slack brief | Markdown brief with priority emojis, @mentions, and ticket links |
| Recurring issue detection | Blockers matched against past meetings via vector similarity |

---

## Screenshots

### Input — paste transcript or upload audio
<img src="https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%201.png?raw=true" width="700"/>

### Agent pipeline — 7 nodes running in sequence
<img src="https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%202.png?raw=true" width="400"/>

### Results — stat cards and follow-up banner
<img src="https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%203.png?raw=true" width="400"/>

### Summary tab — goal, decisions, and open blockers
<img src="https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%204.png?raw=true" width="400"/>

### Action items — routed to Jira, Asana, and Linear automatically
<img src="https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%205.png?raw=true" width="400"/>

### Transcript — speaker-labeled turns with timestamps
<img src="https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%206.png?raw=true" width="400"/>

### Email draft — full HTML summary ready to send
<img src="https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%207.png?raw=true" width="400"/>

### Audio upload — drag and drop .mp3, .m4a, .wav
<img src="https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%208.png?raw=true" width="400"/>

### Audio results — full pipeline output from real recording
<img src="https://github.com/skyplon/ai-meeting-copilot/blob/main/assets/Screenshot%209.png?raw=true" width="400"/>

---

## Architecture

7 LangGraph agents run in a stateful directed graph. Each node has a defined role, typed input/output contract, and explicit tool access. The graph supports conditional branching — the scheduler only fires when unresolved blockers exist — and checkpointing for fault recovery.

```
Audio / Text input
       │
       ▼
┌─────────────────────┐
│  TranscriptionAgent │  OpenAI Whisper → timestamped, diarized transcript
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│    SummaryAgent     │  Claude + Instructor → typed MeetingSummary (Pydantic)
└──────────┬──────────┘
           │
┌──────────▼──────────────┐
│  ActionExtractorAgent   │  Claude tool use → agentic loop until all items extracted
└──────────┬──────────────┘
           │
┌──────────▼──────────┐    ┌─────────────────────┐
│    RouterAgent      │    │    MemoryAgent       │  ← runs sequentially
│  claude-haiku       │    │  Pinecone / mock     │    after Router
│  Jira/Asana/Linear  │    │  recurring detection │
└──────────┬──────────┘    └──────────┬───────────┘
           └──────────────────────────┘
                          │
               follow_up_needed?
                yes ──► SchedulerAgent    Google Calendar MCP
                no  ──► DistributionAgent
                          │
               ┌──────────▼──────────┐
               │  DistributionAgent  │  HTML email + Slack brief
               └──────────┬──────────┘
                          │
                         END
```

---

## Design Decisions and Trade-offs

**LangGraph over a simple sequential chain.** Meeting operations are non-linear. Some meetings need follow-up scheduling; others do not. Some action items belong in Jira; others in Notion. A stateful graph with conditional edges handles this without brittle if/else logic in application code. The tradeoff is added complexity in the graph definition — but it pays off in debuggability and extensibility.

**Claude tool use for action extraction over prompt-based extraction.** Asking Claude to return a JSON list of action items in a single prompt produces inconsistent results, especially in long transcripts where items are buried in context. The tool use approach runs an agentic loop — Claude calls `extract_action_item()` once per item and signals completion with `extraction_complete()`. This is slower but produces higher recall. For a meeting ops tool, missing an action item is a worse failure mode than taking 5 extra seconds.

**Sequential execution over parallel fan-out.** The original design ran RouterAgent and MemoryAgent in parallel using LangGraph's fan-out pattern. This caused `INVALID_CONCURRENT_GRAPH_UPDATE` errors when both agents wrote to shared state fields simultaneously. The fix was to run them sequentially — Router first, then Memory. The performance cost is minimal (~2 seconds) given the overall pipeline duration, and the reliability gain is significant.

**In-memory result store over a database.** Results are stored in a Python dict in the FastAPI process. This means results are lost on server restart. For a portfolio deployment on Render's free tier (which sleeps and restarts), this is a known limitation. The correct production fix is a PostgreSQL store with a UUID-keyed results table, which is a straightforward migration.

**Mock task routing over live MCP integration.** Task routing to Jira, Asana, and Linear produces plausible-looking ticket IDs and URLs but does not create real tickets. Live MCP integration requires OAuth flows and API credentials for each user's workspace — appropriate for a production product, but adds unnecessary setup friction for a demonstration system. The routing classification (which tasks go where) is real and uses claude-haiku as a lightweight classifier.

---

## Success Metrics

These are the metrics a production version of this system would be measured against:

| Metric | Baseline | Target |
|---|---|---|
| Action item capture rate | ~40% in manually-written notes | >90% automatically extracted |
| Time to meeting summary | 24–48 hrs (manual) | <2 minutes (automated) |
| Follow-up scheduling rate | ~20% of meetings with open blockers | 100% of flagged meetings |
| Recurring blocker detection | 0% (no institutional memory) | Match rate >80% on semantically similar blockers |
| Time saved per user per week | 0 | 8–12 hours (estimated based on 4–6 meetings/day) |

---

## Known Limitations

**No real-time transcription.** Audio must be uploaded as a file. Live meeting capture — joining a Zoom or Google Meet call as a bot and transcribing in real time — requires a dedicated bot infrastructure (Recall.ai or AssemblyAI real-time API). The file upload path is sufficient for post-meeting processing but creates friction for users who want zero setup.

**Speaker diarization is approximate.** The current implementation groups transcript segments by pause length to create pseudo-speaker turns. Real speaker identification requires pyannote.audio with a GPU-backed inference server. On Render's free tier, this is not feasible. Speaker labels read as `SPEAKER_00`, `SPEAKER_01` rather than actual names — functional but not production-ready.

**Results do not persist across server restarts.** The Render free tier sleeps after 15 minutes of inactivity. When the server restarts, all in-memory results are lost. Users who process a meeting and return to it later will find it gone. A persistent store would fix this.

**Task routing is mock-only.** Jira, Asana, and Linear links are generated with plausible-looking IDs but do not create real tickets. Live routing requires per-user OAuth configuration for each destination system.

**Memory agent uses keyword matching in demo mode.** Without a Pinecone API key, recurring issue detection falls back to a simple keyword overlap check. It works for obvious matches but will miss semantically similar blockers phrased differently. The full vector similarity path requires a Pinecone index.

**No multi-user isolation.** All meetings are stored in a shared in-process dict. In a multi-user deployment, any user can query any meeting ID. This is acceptable for a single-user portfolio demonstration; it is not acceptable for production.

---

## Roadmap

**Live audio capture via bot injection.**
The highest-value improvement for adoption. Rather than requiring a file upload, a bot joins the calendar invite automatically, transcribes in real time, and begins processing the moment the call ends. Recall.ai provides the bot infrastructure; the rest of the pipeline is unchanged.

**Real speaker diarization.**
Replace the pause-based pseudo-diarization with pyannote.audio 3.0. This requires a GPU inference endpoint but produces speaker labels tied to actual voice profiles — enabling owner resolution that maps "Bob said he'd handle it" to `bob@company.com` with high reliability.

**Persistent results with shareable links.**
Store processed meetings in PostgreSQL with a UUID-keyed results table. Generate a shareable link per meeting so the PM can send attendees a permanent URL to the summary rather than forwarding an email.

**Live MCP integrations for task routing.**
Connect the real Jira, Asana, and Linear MCP servers so task routing creates actual tickets in the user's workspace. This requires an OAuth flow per destination system and a credentials store — the largest single engineering investment on the roadmap but the feature with the clearest ROI signal.

**Cross-meeting intelligence dashboard.**
Aggregate recurring blockers, decision patterns, and action item completion rates across all meetings in a team's history. Surface the top 5 recurring issues this quarter, the average time-to-resolution for blocker categories, and which meeting types generate the most unresolved action items. This is where the episodic memory system pays its biggest dividend.

**Proactive follow-up nudges.**
Track action item due dates against a calendar. Two days before a due date, send the owner a Slack message with the original action item, the meeting context, and a one-click mark-complete. If the item is still open on the due date, escalate to the meeting organizer.

**Fine-tuned action item extractor.**
Use LangSmith traces to collect cases where the action extractor missed items or over-extracted. Fine-tune a haiku-class model on the resulting dataset. The goal is to reduce the tool use loop from 3–5 iterations to 1–2 while maintaining recall above 90%.

---

## Technical Implementation

| Component | Technology | Detail |
|---|---|---|
| Agent orchestration | LangGraph 0.2+ | 7-node stateful graph, conditional edges, MemorySaver checkpointing |
| LLM backbone | claude-haiku-4-5, claude-3-7-sonnet | Haiku for classification/routing, Sonnet for summarization |
| Tool use | Claude native tool use | Agentic extraction loop — iterates until `extraction_complete` is called |
| Structured output | Instructor + Pydantic v2 | Every LLM call returns a typed schema, zero unstructured responses |
| Speech-to-text | OpenAI Whisper API | Timestamped segment output, grouped into pseudo-speaker turns |
| Embeddings | text-embedding-3-small | 1536-dim vectors for episodic memory similarity search |
| Vector store | Pinecone (or in-memory fallback) | Cosine similarity, metadata filtering by meeting/project/date |
| Backend | FastAPI + Uvicorn | REST API, background tasks for audio, in-memory result store |
| Frontend | React 18 + Vite | Upload UI, animated pipeline view, tabbed results dashboard |

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
# Add ANTHROPIC_API_KEY and OPENAI_API_KEY to .env
```

### 2. Install backend
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Start backend
```bash
# Run from project root
cd ~/AI_Prototypes/ai-meeting-copilot
uvicorn backend.api.main:app --reload --port 8000
```

### 4. Start frontend
```bash
cd frontend
npm install && npm run dev
```

Open **http://localhost:5173** and click **Load demo transcript** to test immediately.

### Quick API test
```bash
curl -X POST http://localhost:8000/api/meetings/process-text \
  -H "Content-Type: application/json" \
  -d '{
    "transcript_text": "Alice: Fix the login bug by Friday, it is blocking customers.\nBob: I will handle it. Carlos can you review my PR?\nCarlos: Yes, tag me.\nAlice: We decided to delay the dashboard to Q3.",
    "meeting_title": "Sprint Planning",
    "attendees": ["alice@co.com", "bob@co.com", "carlos@co.com"]
  }'
```

---

## Related Work

- [PM Spec Generator](https://github.com/skyplon/PM-Spec-PRD-Generator) — AI pipeline that turns a feature idea into a developer-ready PRD with competitive research, user stories, and acceptance criteria
- [Prospect-IQ](https://github.com/skyplon/Prospect-IQ) — AI sales intelligence tool for Enterprise SDRs
- [GTM-Ops-Agent](https://github.com/skyplon/GTM-Ops-Agent) — AI-powered GTM planning automation for Sales Operations

---

## Author

**Juan Manuel Navarrete Solano**
Senior Product Manager — Agentic AI & Generative AI

[LinkedIn](https://www.linkedin.com/in/juanmanuelnavarretesolano/) · [GitHub](https://github.com/skyplon)
