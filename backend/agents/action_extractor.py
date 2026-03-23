"""
ActionExtractorAgent
────────────────────
Uses Claude's native tool use to extract action items from the transcript.

Two tools are defined:
  1. extract_action_item  — called once per action item found
  2. extraction_complete  — signals Claude is done (no more items)

This approach lets Claude reason over the transcript iteratively and call
extract_action_item multiple times, once for each task it identifies.
"""

import os
import json
import logging
import anthropic
from ..models.schemas import MeetingState, ActionItem

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ── Tool definitions (passed to Claude) ───────────────────────────────────────

TOOLS = [
    {
        "name": "extract_action_item",
        "description": (
            "Call this once for each action item you find in the transcript. "
            "An action item is a task someone committed to doing, or was assigned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short imperative description of the task, e.g. 'Fix API authentication bug'"
                },
                "owner_name": {
                    "type": "string",
                    "description": "Full name or first name of the person responsible"
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date as ISO string (YYYY-MM-DD) if mentioned, else null"
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Priority inferred from context and urgency language used"
                },
                "source_quote": {
                    "type": "string",
                    "description": "The verbatim transcript sentence this action item came from"
                },
            },
            "required": ["title", "owner_name", "priority", "source_quote"],
        },
    },
    {
        "name": "extraction_complete",
        "description": "Call this when you have extracted ALL action items from the transcript.",
        "input_schema": {
            "type": "object",
            "properties": {
                "total_found": {
                    "type": "integer",
                    "description": "Total number of action items extracted"
                }
            },
            "required": ["total_found"],
        },
    },
]

SYSTEM_PROMPT = """You are an expert at extracting action items from meeting transcripts.

Your job:
1. Read the full transcript carefully
2. Identify every task, commitment, or assignment made by any participant
3. Call extract_action_item() for each one — even implicit ones ("I'll look into that")
4. When done, call extraction_complete()

Priority rules:
- high: involves a deadline, blocker, or urgent language ("ASAP", "by Friday", "blocking")
- low: nice-to-have, future consideration, or vague commitment
- medium: everything else

Be thorough. It is better to extract too many than to miss one."""


def action_extractor_agent(state: MeetingState) -> dict:
    """
    LangGraph node. Reads: transcript, summary.
    Writes: action_items, current_stage, completed_stages.
    """
    logger.info(f"[ActionExtractorAgent] Processing {len(state.transcript)} turns")

    try:
        transcript_text = _format_transcript(state.transcript)
        action_items: list[ActionItem] = []

        # Build context including summary so Claude knows what blockers already exist
        summary_context = ""
        if state.summary:
            summary_context = f"""
<already_known_blockers>
{chr(10).join(f"- {b}" for b in state.summary.blockers)}
</already_known_blockers>
"""

        messages = [{
            "role": "user",
            "content": f"""<meeting_title>{state.meeting_title}</meeting_title>
{summary_context}
<transcript>
{transcript_text}
</transcript>

Extract all action items from this transcript using the provided tools."""
        }]

        # Agentic loop — keep running until extraction_complete is called
        max_iterations = 10
        for iteration in range(max_iterations):
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            # Process tool calls in this response
            done = False
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "extract_action_item":
                        item = _build_action_item(block.input, state.attendees)
                        action_items.append(item)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Extracted: {item.title}",
                        })
                        logger.debug(f"[ActionExtractorAgent] Extracted: {item.title}")

                    elif block.name == "extraction_complete":
                        done = True
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Acknowledged. {block.input.get('total_found', 0)} items extracted.",
                        })

            # If no tool calls were made, we're done
            if not response.content or response.stop_reason == "end_turn":
                break

            if done:
                break

            # Continue the loop with tool results fed back to Claude
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        logger.info(f"[ActionExtractorAgent] Extracted {len(action_items)} action items")

        return {
            "action_items": action_items,
        }

    except Exception as e:
        logger.error(f"[ActionExtractorAgent] Error: {e}")
        return {
            "graph_errors": state.graph_errors + [f"ActionExtractorAgent: {e}"],
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_action_item(tool_input: dict, attendees: list[str]) -> ActionItem:
    """Build an ActionItem, resolving owner email from attendees list."""
    owner_name = tool_input.get("owner_name", "Unknown")
    owner_email = _resolve_email(owner_name, attendees)

    return ActionItem(
        title=tool_input["title"],
        owner_name=owner_name,
        owner_email=owner_email,
        due_date=tool_input.get("due_date"),
        priority=tool_input.get("priority", "medium"),
        source_quote=tool_input.get("source_quote", ""),
    )


def _resolve_email(name: str, attendees: list[str]) -> str | None:
    """
    Simple name→email resolver: check if any attendee email contains
    the owner's first name (case-insensitive).
    """
    first_name = name.split()[0].lower() if name else ""
    for email in attendees:
        local = email.split("@")[0].lower()
        if first_name in local or local in first_name:
            return email
    return None


def _format_transcript(turns) -> str:
    lines = []
    for turn in turns:
        start_min = turn.start_ms // 60000
        start_sec = (turn.start_ms % 60000) // 1000
        lines.append(f"[{start_min:02d}:{start_sec:02d}] {turn.speaker}: {turn.text}")
    return "\n".join(lines)
