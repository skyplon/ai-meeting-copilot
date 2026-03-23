"""
AI Meeting Co-pilot — FastAPI Backend
─────────────────────────────────────
Endpoints:
  POST /api/meetings/process-text   Upload transcript text → run full graph
  POST /api/meetings/process-audio  Upload audio file → run full graph
  GET  /api/meetings/{id}           Fetch result for a meeting ID
  GET  /api/health                  Health check
  WS   /api/meetings/stream/{id}    Stream graph progress (future)

All results are stored in-process (dict) for MVP.
Production: swap for PostgreSQL + async workers.
"""

import os
import uuid
import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from ..models.schemas import (
    MeetingState,
    ProcessMeetingResponse,
    MeetingSummary,
    ActionItem,
    RoutedTask,
)
from ..graph.graph import run_meeting_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── In-process result store (replace with DB in production) ───────────────────
_results: dict[str, dict] = {}
_status: dict[str, str] = {}

UPLOAD_DIR = Path("/tmp/meeting-uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Meeting Co-pilot API starting up")
    yield
    logger.info("AI Meeting Co-pilot API shutting down")


app = FastAPI(
    title="AI Meeting Co-pilot API",
    version="1.0.0",
    description="Agentic meeting ops — transcription, summarization, action extraction, and routing",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite + CRA dev ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request schemas ───────────────────────────────────────────────────────────

class TextRequest(BaseModel):
    transcript_text: str
    meeting_title: str = "Untitled Meeting"
    attendees: list[str] = []


# ── Background runner ─────────────────────────────────────────────────────────

def _run_graph_background(meeting_id: str, initial_state: MeetingState):
    """Runs in a thread pool via BackgroundTasks."""
    _status[meeting_id] = "processing"
    try:
        final_state = run_meeting_graph(initial_state)
        _results[meeting_id] = final_state.model_dump()
        _status[meeting_id] = "done"
        logger.info(f"[API] Graph completed for {meeting_id}")
    except Exception as e:
        logger.error(f"[API] Graph failed for {meeting_id}: {e}")
        _status[meeting_id] = "error"
        _results[meeting_id] = {"error": str(e), "meeting_id": meeting_id}


def _state_to_response(state_dict: dict) -> ProcessMeetingResponse:
    """Converts a state dict to the API response model."""
    summary = None
    if state_dict.get("summary"):
        summary = MeetingSummary(**state_dict["summary"])

    action_items = [ActionItem(**a) for a in state_dict.get("action_items", [])]

    routed_tasks = []
    for rt in state_dict.get("routed_tasks", []):
        if isinstance(rt.get("action_item"), dict):
            rt["action_item"] = ActionItem(**rt["action_item"])
        routed_tasks.append(RoutedTask(**rt))

    follow_up = None
    if state_dict.get("follow_up_event"):
        from ..models.schemas import CalendarEvent
        follow_up = CalendarEvent(**state_dict["follow_up_event"])

    from ..models.schemas import Turn
    transcript = [Turn(**t) for t in state_dict.get("transcript", [])]

    return ProcessMeetingResponse(
        meeting_id=state_dict.get("meeting_id", "unknown"),
        status=_status.get(state_dict.get("meeting_id", ""), "done"),
        summary=summary,
        action_items=action_items,
        routed_tasks=routed_tasks,
        follow_up_event=follow_up,
        recurring_issues=state_dict.get("recurring_issues", []),
        transcript=transcript,
        errors=state_dict.get("graph_errors", []),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/meetings/process-text", response_model=ProcessMeetingResponse)
async def process_text(request: TextRequest, background_tasks: BackgroundTasks):
    """
    Accepts a pasted or pre-formatted transcript and runs the full agent graph.
    Returns immediately with meeting_id; poll /api/meetings/{id} for status.
    """
    if not request.transcript_text.strip():
        raise HTTPException(status_code=400, detail="transcript_text cannot be empty")

    meeting_id = str(uuid.uuid4())
    initial_state = MeetingState(
        meeting_id=meeting_id,
        meeting_title=request.meeting_title,
        attendees=request.attendees,
        transcript_text=request.transcript_text,
    )

    _status[meeting_id] = "queued"

    # Run synchronously for MVP (simpler for demo); swap for background task for prod
    try:
        final_state = run_meeting_graph(initial_state)
        _results[meeting_id] = final_state.model_dump()
        _status[meeting_id] = "done"
        return _state_to_response(_results[meeting_id])
    except Exception as e:
        logger.error(f"[API] Graph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/meetings/process-audio", response_model=dict)
async def process_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    meeting_title: str = Form("Untitled Meeting"),
    attendees: str = Form(""),          # comma-separated emails
):
    """
    Accepts an audio file upload (.mp3, .mp4, .wav, .m4a).
    Processing runs in background; poll /api/meetings/{id} for results.
    """
    allowed = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".webm"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}. Use: {allowed}")

    meeting_id = str(uuid.uuid4())
    audio_path = UPLOAD_DIR / f"{meeting_id}{suffix}"

    # Save upload to disk
    content = await file.read()
    audio_path.write_bytes(content)
    logger.info(f"[API] Saved audio to {audio_path} ({len(content):,} bytes)")

    attendee_list = [e.strip() for e in attendees.split(",") if e.strip()]
    initial_state = MeetingState(
        meeting_id=meeting_id,
        meeting_title=meeting_title,
        attendees=attendee_list,
        audio_path=str(audio_path),
    )

    _status[meeting_id] = "queued"

    # Run in background so the request returns immediately
    background_tasks.add_task(_run_graph_background, meeting_id, initial_state)

    return {"meeting_id": meeting_id, "status": "queued", "message": "Processing started — poll /api/meetings/{id}"}


@app.get("/api/meetings/{meeting_id}", response_model=ProcessMeetingResponse)
def get_meeting(meeting_id: str):
    """Poll endpoint to check processing status and retrieve results."""
    if meeting_id not in _status:
        raise HTTPException(status_code=404, detail="Meeting not found")

    status = _status[meeting_id]

    if status in ("queued", "processing"):
        return ProcessMeetingResponse(
            meeting_id=meeting_id,
            status=status,
        )

    if status == "error":
        err = _results.get(meeting_id, {}).get("error", "Unknown error")
        raise HTTPException(status_code=500, detail=err)

    return _state_to_response(_results[meeting_id])


@app.get("/api/meetings/{meeting_id}/email")
def get_email_draft(meeting_id: str):
    """Returns the HTML email draft for a completed meeting."""
    if meeting_id not in _results:
        raise HTTPException(status_code=404, detail="Meeting not found or not yet processed")
    email_html = _results[meeting_id].get("email_html", "")
    if not email_html:
        return JSONResponse({"html": "<p>Email not generated — distribution agent may have errored.</p>"})
    return JSONResponse({"html": email_html})


@app.get("/api/meetings/{meeting_id}/slack")
def get_slack_brief(meeting_id: str):
    """Returns the Slack brief markdown for a completed meeting."""
    if meeting_id not in _results:
        raise HTTPException(status_code=404, detail="Meeting not found or not yet processed")
    slack_brief = _results[meeting_id].get("slack_brief", "")
    if not slack_brief:
        return JSONResponse({"markdown": "Slack brief not generated — distribution agent may have errored."})
    return JSONResponse({"markdown": slack_brief})


@app.get("/api/meetings")
def list_meetings():
    """Returns a list of all processed meetings (for the demo dashboard)."""
    return {
        "meetings": [
            {"meeting_id": mid, "status": status}
            for mid, status in _status.items()
        ]
    }
