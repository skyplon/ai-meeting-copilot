"""
SummaryAgent
────────────
Uses Claude (claude-3-7-sonnet) with Instructor to produce a strictly typed
MeetingSummary from the diarized transcript.

Key technique: Instructor patches the Anthropic client to enforce the
Pydantic schema — zero chance of getting back a string blob.
"""

import os
import logging
import anthropic
import instructor
from ..models.schemas import MeetingState, MeetingSummary

logger = logging.getLogger(__name__)

# Instructor patches the Anthropic client to support response_model=
anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
client = instructor.from_anthropic(anthropic_client)

SYSTEM_PROMPT = """You are an expert meeting analyst. Your job is to extract structured insights 
from meeting transcripts with surgical precision.

Rules:
- Be concise. Decisions should be one sentence each.
- Blockers are issues explicitly raised but NOT resolved by end of meeting.
- Quotes must be verbatim from the transcript (or very close).
- Set follow_up_needed=true only if at least one blocker remains open.
- Mood is your holistic read of the meeting tone.
"""


def summary_agent(state: MeetingState) -> dict:
    """
    LangGraph node. Reads: transcript.
    Writes: summary, current_stage, completed_stages.
    """
    logger.info(f"[SummaryAgent] Summarizing {len(state.transcript)} turns")

    try:
        transcript_text = _format_transcript(state.transcript)

        summary: MeetingSummary = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"""<meeting_title>{state.meeting_title}</meeting_title>

<transcript>
{transcript_text}
</transcript>

Extract the structured meeting summary from this transcript."""
            }],
            response_model=MeetingSummary,
        )

        logger.info(f"[SummaryAgent] Summary: goal='{summary.goal[:60]}...', "
                    f"decisions={len(summary.decisions)}, blockers={len(summary.blockers)}")

        return {
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"[SummaryAgent] Error: {e}")
        return {
            "graph_errors": state.graph_errors + [f"SummaryAgent: {e}"],
        }


def _format_transcript(turns) -> str:
    """Format turns as readable dialogue for the LLM prompt."""
    lines = []
    for turn in turns:
        start_min = turn.start_ms // 60000
        start_sec = (turn.start_ms % 60000) // 1000
        lines.append(f"[{start_min:02d}:{start_sec:02d}] {turn.speaker}: {turn.text}")
    return "\n".join(lines)
