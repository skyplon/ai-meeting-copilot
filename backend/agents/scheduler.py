"""
SchedulerAgent
──────────────
Creates a follow-up calendar event when the summary indicates
unresolved blockers that need a follow-up meeting.

MVP: generates a mock calendar event with a Google Calendar "create event" URL
     that the user can click to add it themselves.

Production: replace with gcal_create_event via Google Calendar MCP server.
"""

import os
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode
import anthropic
import instructor
from ..models.schemas import MeetingState, CalendarEvent

logger = logging.getLogger(__name__)

anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
client = instructor.from_anthropic(anthropic_client)


class FollowUpEvent(CalendarEvent):
    """Extends CalendarEvent with a click-to-add URL."""
    pass


def scheduler_agent(state: MeetingState) -> dict:
    """
    LangGraph node. Reads: summary, attendees, meeting_title.
    Writes: follow_up_event, current_stage, completed_stages.

    Only fires if summary.follow_up_needed is True.
    """
    if not state.summary or not state.summary.follow_up_needed:
        logger.info("[SchedulerAgent] No follow-up needed — skipping")
        return {
        }

    logger.info("[SchedulerAgent] Creating follow-up event")

    try:
        # ── Generate event details with Claude ────────────────────────────────
        blockers_text = "\n".join(f"- {b}" for b in state.summary.blockers)

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": f"""
Create a follow-up meeting event for these unresolved blockers:

Meeting: {state.meeting_title}
Blockers:
{blockers_text}

Return a CalendarEvent with:
- title: brief descriptive meeting title (max 60 chars)
- description: agenda based on the blockers (max 200 chars)
- start_datetime: next business day at 10:00 AM (today is {datetime.now().strftime('%Y-%m-%d')})
- end_datetime: 30 minutes after start
- attendees: {state.attendees}
"""}],
            response_model=CalendarEvent,
        )

        # Build a Google Calendar "quick add" URL the user can click
        event_url = _build_gcal_url(response, state.attendees)
        follow_up = response.model_copy(update={
            "attendees": state.attendees,
            "event_url": event_url,
        })

        logger.info(f"[SchedulerAgent] Created event: {follow_up.title}")

        return {
            "follow_up_event": follow_up,
        }

    except Exception as e:
        logger.error(f"[SchedulerAgent] Error: {e}")
        return {
            "graph_errors": state.graph_errors + [f"SchedulerAgent: {e}"],
        }


def _build_gcal_url(event: CalendarEvent, attendees: list[str]) -> str:
    """Builds a Google Calendar event creation URL (no auth required)."""
    try:
        start = datetime.fromisoformat(event.start_datetime)
        end = datetime.fromisoformat(event.end_datetime)
        fmt = "%Y%m%dT%H%M%S"
        params = {
            "action": "TEMPLATE",
            "text": event.title,
            "dates": f"{start.strftime(fmt)}/{end.strftime(fmt)}",
            "details": event.description,
            "add": ",".join(attendees),
        }
        return "https://calendar.google.com/calendar/render?" + urlencode(params)
    except Exception:
        return "https://calendar.google.com/calendar/r/eventedit"
