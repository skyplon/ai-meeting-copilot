"""
DistributionAgent
─────────────────
Produces two distribution artifacts from all upstream agent outputs:

1. Email draft (HTML body + plain text fallback) — ready to send via Gmail
2. Slack brief (markdown-formatted) — ready to post to a channel

MVP: returns the content as strings (no actual sending).
Production: 
  - Email → Gmail MCP (gmail_create_draft)
  - Slack  → Slack Bolt SDK (client.chat_postMessage)
"""

import os
import logging
import anthropic
from ..models.schemas import MeetingState

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def distribution_agent(state: MeetingState) -> dict:
    """
    LangGraph node. Reads: everything upstream.
    Writes: email_draft (stored on state via graph_errors hack for now),
            slack_posted, current_stage, completed_stages.
    """
    logger.info("[DistributionAgent] Generating distribution content")

    try:
        email_html = _generate_email(state)
        slack_brief = _generate_slack_brief(state)

        # In production: call Gmail MCP to create draft + Slack SDK to post
        # For MVP: log and return (API surfaces these in the response)
        logger.info("[DistributionAgent] Email and Slack content generated")

        return {
            "email_draft_id": "draft_generated",
            "slack_posted": False,
            "email_html": email_html,
            "slack_brief": slack_brief,
        }

    except Exception as e:
        logger.error(f"[DistributionAgent] Error: {e}")
        return {
            "graph_errors": state.graph_errors + [f"DistributionAgent: {e}"],
        }


# ── Email generator ───────────────────────────────────────────────────────────

def _generate_email(state: MeetingState) -> str:
    """Generates an HTML email body using Claude."""
    summary = state.summary
    if not summary:
        return "<p>Meeting summary unavailable.</p>"

    actions_html = ""
    for item in state.routed_tasks:
        ai = item.action_item
        badge_color = {"high": "#DC2626", "medium": "#D97706", "low": "#16A34A"}.get(ai.priority, "#64748B")
        link = f'<a href="{item.url}" style="color:#2563EB">{item.tool.upper()} ↗</a>' if item.url else item.tool.upper()
        due = f" · Due {ai.due_date}" if ai.due_date else ""
        actions_html += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0">{ai.title}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0">{ai.owner_name}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0">
            <span style="background:{badge_color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">{ai.priority.upper()}</span>{due}
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0">{link}</td>
        </tr>"""

    blockers_html = "".join(f"<li style='margin-bottom:6px'>{b}</li>" for b in summary.blockers)
    decisions_html = "".join(f"<li style='margin-bottom:6px'>{d}</li>" for d in summary.decisions)

    followup_section = ""
    if state.follow_up_event:
        e = state.follow_up_event
        followup_section = f"""
        <div style="background:#EFF6FF;border-left:4px solid #2563EB;padding:16px;margin:20px 0;border-radius:0 8px 8px 0">
          <strong style="color:#1E40AF">📅 Follow-up scheduled</strong><br>
          <strong>{e.title}</strong> · {e.start_datetime[:16].replace('T', ' at ')}<br>
          <a href="{e.event_url}" style="color:#2563EB;margin-top:6px;display:inline-block">Add to calendar ↗</a>
        </div>"""

    recurring_section = ""
    if state.recurring_issues:
        items = "".join(f"<li>{r}</li>" for r in state.recurring_issues)
        recurring_section = f"""
        <div style="background:#FEF3C7;border-left:4px solid #D97706;padding:16px;margin:20px 0;border-radius:0 8px 8px 0">
          <strong style="color:#92400E">⚠️ Recurring issues detected</strong>
          <ul style="margin:8px 0 0;padding-left:20px">{items}</ul>
        </div>"""

    mood_emoji = {"productive": "✅", "aligned": "🤝", "tense": "⚡", "unclear": "❓"}.get(summary.mood, "📋")

    return f"""
<div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;color:#1E293B">
  <div style="background:#1B2E4B;color:#fff;padding:24px 32px;border-radius:8px 8px 0 0">
    <h1 style="margin:0;font-size:22px">Meeting Summary</h1>
    <p style="margin:6px 0 0;opacity:.8;font-size:14px">{state.meeting_title} · {mood_emoji} {summary.mood.title()}</p>
  </div>

  <div style="background:#fff;border:1px solid #E2E8F0;border-top:none;padding:24px 32px">

    <div style="background:#F8FAFC;border-left:4px solid #1B2E4B;padding:16px;border-radius:0 8px 8px 0;margin-bottom:24px">
      <strong style="font-size:13px;color:#64748B;text-transform:uppercase;letter-spacing:.05em">Meeting goal</strong>
      <p style="margin:6px 0 0;font-size:16px">{summary.goal}</p>
    </div>

    <h3 style="color:#334155;border-bottom:1px solid #E2E8F0;padding-bottom:8px">Decisions made</h3>
    <ul style="padding-left:20px;line-height:1.8">{decisions_html or "<li>No firm decisions recorded</li>"}</ul>

    <h3 style="color:#334155;border-bottom:1px solid #E2E8F0;padding-bottom:8px">Open blockers</h3>
    <ul style="padding-left:20px;line-height:1.8">{blockers_html or "<li>No open blockers 🎉</li>"}</ul>

    {recurring_section}
    {followup_section}

    <h3 style="color:#334155;border-bottom:1px solid #E2E8F0;padding-bottom:8px">Action items ({len(state.routed_tasks)})</h3>
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <thead>
        <tr style="background:#F1F5F9">
          <th style="padding:10px 12px;text-align:left;border-bottom:2px solid #CBD5E1">Task</th>
          <th style="padding:10px 12px;text-align:left;border-bottom:2px solid #CBD5E1">Owner</th>
          <th style="padding:10px 12px;text-align:left;border-bottom:2px solid #CBD5E1">Priority</th>
          <th style="padding:10px 12px;text-align:left;border-bottom:2px solid #CBD5E1">Ticket</th>
        </tr>
      </thead>
      <tbody>{actions_html or '<tr><td colspan="4" style="padding:12px;color:#94A3B8">No action items extracted</td></tr>'}</tbody>
    </table>

  </div>
  <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-top:none;padding:12px 32px;border-radius:0 0 8px 8px">
    <p style="font-size:12px;color:#94A3B8;margin:0">Generated by AI Meeting Co-pilot · Not for external distribution</p>
  </div>
</div>"""


# ── Slack brief generator ─────────────────────────────────────────────────────

def _generate_slack_brief(state: MeetingState) -> str:
    """Generates a Slack markdown brief."""
    summary = state.summary
    if not summary:
        return f"*{state.meeting_title}* — Summary unavailable"

    mood_emoji = {"productive": "✅", "aligned": "🤝", "tense": "⚡", "unclear": "❓"}.get(summary.mood, "📋")

    lines = [
        f"*{mood_emoji} Meeting Summary: {state.meeting_title}*",
        f"> {summary.goal}",
        "",
    ]

    if summary.decisions:
        lines.append("*Decisions:*")
        for d in summary.decisions:
            lines.append(f"• {d}")
        lines.append("")

    if summary.blockers:
        lines.append("*Open blockers:*")
        for b in summary.blockers:
            lines.append(f"• ⚠️ {b}")
        lines.append("")

    if state.routed_tasks:
        lines.append(f"*Action items ({len(state.routed_tasks)}):*")
        for task in state.routed_tasks:
            ai = task.action_item
            priority_badge = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(ai.priority, "⚪")
            owner = f"<mailto:{ai.owner_email}|{ai.owner_name}>" if ai.owner_email else ai.owner_name
            link = f" → <{task.url}|{task.tool.upper()}>" if task.url else f" → {task.tool.upper()}"
            due = f" · _{ai.due_date}_" if ai.due_date else ""
            lines.append(f"{priority_badge} *{ai.title}* — {owner}{due}{link}")
        lines.append("")

    if state.follow_up_event:
        e = state.follow_up_event
        lines.append(f"*📅 Follow-up:* {e.title} — {e.start_datetime[:16].replace('T', ' at ')}")
        if e.event_url:
            lines.append(f"<{e.event_url}|Add to calendar>")

    return "\n".join(lines)
