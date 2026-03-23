"""
RouterAgent
───────────
Classifies each action item by destination tool and creates the task.

Routing logic:
  - Engineering tasks (bugs, builds, deploys, code) → Jira
  - Design tasks → Linear  
  - Notes / docs / reference → Notion
  - Meetings / calls / reviews → Calendar
  - Everything else → Asana (default PM tool)

For the MVP we use mock task creation that returns fake IDs.
To go live, uncomment the MCP sections and set your API tokens.
"""

import os
import json
import logging
import anthropic
from ..models.schemas import MeetingState, ActionItem, RoutedTask

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ── Routing rules (few-shot examples for the classifier) ─────────────────────
ROUTING_SYSTEM = """You are a task router. Given an action item title, output ONLY a JSON object:
{"destination": "<tool>"}

Tool choices:
- "jira"     → engineering: bugs, code reviews, deployments, tech debt, API work
- "linear"   → design: UI/UX mockups, design reviews, figma work
- "notion"   → docs: write-ups, notes, research, documentation
- "calendar" → scheduling: meetings, calls, demos, reviews that need calendar events
- "asana"    → everything else (default for PM / cross-team tasks)

Examples:
"Fix authentication bug in login flow" → {"destination": "jira"}
"Design new onboarding screens" → {"destination": "linear"}
"Write Q2 roadmap document" → {"destination": "notion"}
"Schedule design review with the team" → {"destination": "calendar"}
"Align with sales on pricing changes" → {"destination": "asana"}
"""


def router_agent(state: MeetingState) -> dict:
    """
    LangGraph node. Reads: action_items.
    Writes: routed_tasks, current_stage, completed_stages.
    """
    logger.info(f"[RouterAgent] Routing {len(state.action_items)} action items")

    if not state.action_items:
        return {
            "routed_tasks": [],
        }

    routed: list[RoutedTask] = []
    errors = list(state.graph_errors)

    for item in state.action_items:
        try:
            destination = _classify_destination(item.title)
            item_with_dest = item.model_copy(update={"destination": destination})
            task = _create_task(item_with_dest, destination)
            routed.append(task)
            logger.debug(f"[RouterAgent] '{item.title[:40]}' → {destination}")
        except Exception as e:
            logger.error(f"[RouterAgent] Failed to route '{item.title}': {e}")
            errors.append(f"RouterAgent: failed to route '{item.title}': {e}")
            # Still include as un-routed rather than losing the item
            routed.append(RoutedTask(action_item=item, tool="unrouted"))

    return {
        "routed_tasks": routed,
        "graph_errors": errors,
    }


# ── Classifier ────────────────────────────────────────────────────────────────

def _classify_destination(title: str) -> str:
    """Use claude-haiku for fast, cheap classification."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=64,
        system=ROUTING_SYSTEM,
        messages=[{"role": "user", "content": title}],
    )
    text = response.content[0].text.strip()
    try:
        result = json.loads(text)
        return result.get("destination", "asana")
    except json.JSONDecodeError:
        # Fallback: scan for known keywords
        title_lower = title.lower()
        if any(k in title_lower for k in ["bug", "fix", "deploy", "api", "code", "backend"]):
            return "jira"
        if any(k in title_lower for k in ["design", "ui", "ux", "mockup", "figma"]):
            return "linear"
        if any(k in title_lower for k in ["doc", "write", "note", "research"]):
            return "notion"
        if any(k in title_lower for k in ["schedule", "meeting", "call", "review"]):
            return "calendar"
        return "asana"


# ── Task creators (mock for MVP, real API calls in production) ────────────────

def _create_task(item: ActionItem, destination: str) -> RoutedTask:
    """
    MVP: mock task creation returns plausible fake IDs and URLs.
    Production: replace each branch with the real MCP tool call or SDK.
    """
    creators = {
        "jira":     _mock_jira,
        "asana":    _mock_asana,
        "linear":   _mock_linear,
        "notion":   _mock_notion,
        "calendar": _mock_calendar_task,
    }
    creator = creators.get(destination, _mock_asana)
    external_id, url = creator(item)

    return RoutedTask(
        action_item=item,
        tool=destination,
        external_id=external_id,
        url=url,
    )


def _mock_jira(item: ActionItem):
    import hashlib
    ticket_num = abs(hash(item.title)) % 9000 + 1000
    return f"ENG-{ticket_num}", f"https://your-org.atlassian.net/browse/ENG-{ticket_num}"


def _mock_asana(item: ActionItem):
    task_id = abs(hash(item.title)) % 900000000000 + 100000000000
    return str(task_id), f"https://app.asana.com/0/inbox/{task_id}"


def _mock_linear(item: ActionItem):
    import random, string
    short = "".join(random.choices(string.ascii_uppercase, k=3))
    num = abs(hash(item.title)) % 900 + 100
    return f"{short}-{num}", f"https://linear.app/your-org/issue/{short}-{num}"


def _mock_notion(item: ActionItem):
    import uuid
    page_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, item.title)).replace("-", "")
    return page_id[:8], f"https://notion.so/{page_id}"


def _mock_calendar_task(item: ActionItem):
    event_id = abs(hash(item.title)) % 9000000 + 1000000
    return str(event_id), f"https://calendar.google.com/calendar/r/eventedit?text={item.title.replace(' ', '+')}"


# ── Real MCP integration (uncomment when ready) ───────────────────────────────
#
# To route to real Asana via MCP:
#
# async def _real_asana(item: ActionItem):
#     response = await anthropic_client.messages.create(
#         model="claude-haiku-4-5-20251001",
#         max_tokens=512,
#         mcp_servers=[{"type": "url", "url": "https://mcp.asana.com/sse", "name": "asana"}],
#         messages=[{"role": "user", "content": f"""
#             Create a task in Asana:
#             Title: {item.title}
#             Assignee: {item.owner_email}
#             Due date: {item.due_date}
#         """}],
#     )
#     # Parse the task_id from the MCP tool result block
#     ...
