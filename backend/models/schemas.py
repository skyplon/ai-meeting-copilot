"""
Shared Pydantic models and LangGraph state schema.
Every agent reads from / writes to MeetingState.
"""

from __future__ import annotations
from typing import Annotated, Any, Literal, Optional
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


# ── Transcript ────────────────────────────────────────────────────────────────

class Turn(BaseModel):
    speaker: str          # e.g. "SPEAKER_00" or resolved "Alice"
    text: str
    start_ms: int
    end_ms: int


# ── Summary ───────────────────────────────────────────────────────────────────

class QuoteWithSpeaker(BaseModel):
    speaker: str
    quote: str


class MeetingSummary(BaseModel):
    goal: str = Field(description="The main objective of the meeting in one sentence")
    decisions: list[str] = Field(description="Concrete decisions made during the meeting")
    blockers: list[str] = Field(description="Open issues or blockers raised but not resolved")
    key_quotes: list[QuoteWithSpeaker] = Field(default_factory=list)
    mood: Literal["productive", "tense", "unclear", "aligned"] = "productive"
    follow_up_needed: bool = Field(description="True if unresolved blockers require a follow-up meeting")


# ── Action Items ──────────────────────────────────────────────────────────────

class ActionItem(BaseModel):
    title: str
    owner_name: str
    owner_email: Optional[str] = None
    due_date: Optional[str] = None          # ISO date string e.g. "2026-04-01"
    priority: Literal["high", "medium", "low"] = "medium"
    source_quote: str = Field(description="Verbatim transcript sentence this was extracted from")
    destination: Optional[str] = None       # Set by RouterAgent: "asana"|"jira"|"notion"|"calendar"


class RoutedTask(BaseModel):
    action_item: ActionItem
    tool: str                               # "asana", "jira", "notion", "calendar"
    external_id: Optional[str] = None      # ID in the destination system
    url: Optional[str] = None              # Link to created task


# ── Calendar ──────────────────────────────────────────────────────────────────

class CalendarEvent(BaseModel):
    title: str
    start_datetime: str                     # ISO 8601
    end_datetime: str
    attendees: list[str]                    # email addresses
    description: str
    event_id: Optional[str] = None
    event_url: Optional[str] = None


# ── LangGraph State ───────────────────────────────────────────────────────────

class MeetingState(BaseModel):
    """
    The single shared state object that flows through the entire LangGraph.
    Each agent reads what it needs and writes its outputs back here.
    """
    # Inputs
    meeting_id: str
    audio_path: Optional[str] = None
    transcript_text: Optional[str] = None   # Alternative: paste raw transcript text
    attendees: list[str] = Field(default_factory=list)   # ["alice@co.com", "bob@co.com"]
    meeting_title: str = "Meeting"

    # Agent outputs (populated as graph runs)
    transcript: list[Turn] = Field(default_factory=list)
    summary: Optional[MeetingSummary] = None
    action_items: list[ActionItem] = Field(default_factory=list)
    routed_tasks: list[RoutedTask] = Field(default_factory=list)
    follow_up_event: Optional[CalendarEvent] = None
    recurring_issues: list[str] = Field(default_factory=list)
    email_draft_id: Optional[str] = None
    slack_posted: bool = False

    # Error tracking — never swallow, always surface
    graph_errors: list[str] = Field(default_factory=list)

    # Distribution outputs
    email_html: Optional[str] = None
    slack_brief: Optional[str] = None

    # Status tracking for the UI
    current_stage: str = "pending"          # transcription|summarizing|extracting|routing|scheduling|distributing|done
    completed_stages: list[str] = Field(default_factory=list)


# ── API request/response ──────────────────────────────────────────────────────

class ProcessMeetingRequest(BaseModel):
    meeting_title: str = "Untitled Meeting"
    attendees: list[str] = Field(default_factory=list)
    transcript_text: Optional[str] = None   # If provided, skip transcription


class ProcessMeetingResponse(BaseModel):
    meeting_id: str
    status: str
    summary: Optional[MeetingSummary] = None
    action_items: list[ActionItem] = Field(default_factory=list)
    routed_tasks: list[RoutedTask] = Field(default_factory=list)
    follow_up_event: Optional[CalendarEvent] = None
    recurring_issues: list[str] = Field(default_factory=list)
    transcript: list[Turn] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
