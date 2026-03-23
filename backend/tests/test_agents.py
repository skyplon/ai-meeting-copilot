"""
Tests for AI Meeting Co-pilot agents.

Run with:  pytest tests/ -v
Requires:  ANTHROPIC_API_KEY and OPENAI_API_KEY in env (or set in .env)

Tests are marked:
  @pytest.mark.unit    — no API calls, runs instantly
  @pytest.mark.api     — makes real API calls, costs ~$0.01 per run
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.models.schemas import (
    MeetingState, MeetingSummary, ActionItem, Turn,
    RoutedTask, CalendarEvent
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

DEMO_TRANSCRIPT = """Alice Chen: We need to fix the authentication bug by Thursday — it's blocking three customers.
Bob Martinez: Agreed. I'll own the fix. Should take about two days. Carlos, can you review the PR?
Carlos Ruiz: Yes, I'll review by Wednesday. Just tag me.
Alice Chen: Great. Also, we've decided to delay the analytics dashboard to Q3 and focus on the mobile rewrite.
Bob Martinez: Makes sense. Who leads the mobile rewrite?
Alice Chen: Carlos will lead it. Carlos, can you write the technical spec by end of next week?
Carlos Ruiz: Sure. I'll need design mockups first though — that's a blocker for me.
Alice Chen: I'll ask the design team today. Also, we still don't have a payment provider decision. That's been blocking checkout for two weeks.
Bob Martinez: I'll file a P1 ticket for the staging environment issue as well — it keeps going down.
Alice Chen: Good. Let's wrap up. I'll schedule a follow-up for Friday."""


@pytest.fixture
def sample_state():
    return MeetingState(
        meeting_id="test-meeting-001",
        meeting_title="Sprint Planning",
        attendees=["alice@company.com", "bob@company.com", "carlos@company.com"],
        transcript_text=DEMO_TRANSCRIPT,
    )


@pytest.fixture
def state_with_transcript(sample_state):
    """State after transcription has run."""
    return sample_state.model_copy(update={
        "transcript": [
            Turn(speaker="Alice Chen", text="We need to fix the authentication bug by Thursday.", start_ms=0, end_ms=5000),
            Turn(speaker="Bob Martinez", text="Agreed. I'll own the fix. Carlos, can you review the PR?", start_ms=5500, end_ms=11000),
            Turn(speaker="Carlos Ruiz", text="Yes, I'll review by Wednesday.", start_ms=11500, end_ms=14000),
            Turn(speaker="Alice Chen", text="Great. We've decided to delay the analytics dashboard to Q3.", start_ms=14500, end_ms=19000),
            Turn(speaker="Bob Martinez", text="I'll file a P1 ticket for the staging environment issue.", start_ms=19500, end_ms=24000),
        ],
        "current_stage": "summarizing",
        "completed_stages": ["transcription"],
    })


@pytest.fixture
def state_with_summary(state_with_transcript):
    return state_with_transcript.model_copy(update={
        "summary": MeetingSummary(
            goal="Align on Q2 roadmap and unblock the API integration work",
            decisions=[
                "Delay analytics dashboard to Q3",
                "Carlos will lead the mobile rewrite",
                "Bob will own the authentication bug fix",
            ],
            blockers=[
                "Design mockups needed before Carlos can finalize mobile spec",
                "Payment provider decision still pending — blocking checkout flow",
                "Staging environment intermittently down",
            ],
            follow_up_needed=True,
            mood="productive",
        ),
        "current_stage": "extracting",
        "completed_stages": ["transcription", "summarizing"],
    })


@pytest.fixture
def state_with_actions(state_with_summary):
    return state_with_summary.model_copy(update={
        "action_items": [
            ActionItem(title="Fix authentication bug", owner_name="Bob Martinez",
                       owner_email="bob@company.com", due_date="2026-03-27",
                       priority="high", source_quote="I'll own the fix. Should take about two days."),
            ActionItem(title="Write mobile rewrite technical spec", owner_name="Carlos Ruiz",
                       owner_email="carlos@company.com", due_date="2026-03-29",
                       priority="high", source_quote="Carlos, can you write the technical spec by end of next week?"),
            ActionItem(title="Request design mockups from design team", owner_name="Alice Chen",
                       owner_email="alice@company.com",
                       priority="medium", source_quote="I'll ask the design team today."),
            ActionItem(title="Schedule payment provider decision meeting", owner_name="Alice Chen",
                       owner_email="alice@company.com",
                       priority="high", source_quote="we still don't have a payment provider decision"),
            ActionItem(title="File P1 ticket for staging environment", owner_name="Bob Martinez",
                       owner_email="bob@company.com",
                       priority="medium", source_quote="I'll file a P1 ticket for the staging environment issue."),
        ],
        "current_stage": "routing",
        "completed_stages": ["transcription", "summarizing", "extracting"],
    })


# ══════════════════════════════════════════════════════════════════════════════
# Unit tests — no API calls
# ══════════════════════════════════════════════════════════════════════════════

class TestTranscriptionParsing:
    """Tests for the text transcript parser."""

    @pytest.mark.unit
    def test_parses_labeled_transcript(self, sample_state):
        from backend.agents.transcription import _parse_text_transcript
        turns = _parse_text_transcript(DEMO_TRANSCRIPT)
        assert len(turns) > 0
        speakers = {t.speaker for t in turns}
        assert "Alice Chen" in speakers or "Alice" in " ".join(speakers)

    @pytest.mark.unit
    def test_parses_plain_text(self):
        from backend.agents.transcription import _parse_text_transcript
        plain = "We need to ship by Friday.\nI agree, the bug is critical.\nLet's plan for Thursday."
        turns = _parse_text_transcript(plain)
        assert len(turns) > 0
        assert all(t.text for t in turns)

    @pytest.mark.unit
    def test_turn_timestamps_are_sequential(self, sample_state):
        from backend.agents.transcription import _parse_text_transcript
        turns = _parse_text_transcript(DEMO_TRANSCRIPT)
        for i in range(1, len(turns)):
            assert turns[i].start_ms >= turns[i-1].start_ms

    @pytest.mark.unit
    def test_empty_transcript_returns_empty_list(self):
        from backend.agents.transcription import _parse_text_transcript
        turns = _parse_text_transcript("")
        assert turns == []

    @pytest.mark.unit
    def test_single_line_transcript(self):
        from backend.agents.transcription import _parse_text_transcript
        turns = _parse_text_transcript("Alice: We need to ship.")
        assert len(turns) == 1
        assert turns[0].text == "We need to ship."


class TestRouterAgent:
    """Tests for the routing classifier — mocks the Claude API."""

    @pytest.mark.unit
    def test_routes_bug_to_jira(self, state_with_actions):
        from backend.agents.router import _classify_destination
        with patch("backend.agents.router.client") as mock_client:
            mock_client.messages.create.return_value = MagicMock(
                content=[MagicMock(text='{"destination": "jira"}')]
            )
            dest = _classify_destination("Fix authentication bug in login flow")
            assert dest == "jira"

    @pytest.mark.unit
    def test_routes_design_to_linear(self):
        from backend.agents.router import _classify_destination
        with patch("backend.agents.router.client") as mock_client:
            mock_client.messages.create.return_value = MagicMock(
                content=[MagicMock(text='{"destination": "linear"}')]
            )
            dest = _classify_destination("Create mockup designs for mobile onboarding")
            assert dest == "linear"

    @pytest.mark.unit
    def test_fallback_on_invalid_json(self):
        from backend.agents.router import _classify_destination
        with patch("backend.agents.router.client") as mock_client:
            mock_client.messages.create.return_value = MagicMock(
                content=[MagicMock(text="I'll route this to asana")]  # invalid JSON
            )
            dest = _classify_destination("Align with sales team on Q2 targets")
            assert dest in ["asana", "jira", "linear", "notion", "calendar"]

    @pytest.mark.unit
    def test_keyword_fallback_jira(self):
        from backend.agents.router import _classify_destination
        with patch("backend.agents.router.client") as mock_client:
            mock_client.messages.create.return_value = MagicMock(
                content=[MagicMock(text="invalid")]
            )
            dest = _classify_destination("fix the api bug in backend")
            assert dest == "jira"

    @pytest.mark.unit
    def test_router_handles_empty_action_items(self):
        from backend.agents.router import router_agent
        empty_state = MeetingState(meeting_id="test", action_items=[])
        result = router_agent(empty_state)
        assert result["routed_tasks"] == []

    @pytest.mark.unit
    def test_mock_jira_ticket_format(self):
        from backend.agents.router import _mock_jira
        item = ActionItem(title="Fix login bug", owner_name="Bob",
                          priority="high", source_quote="we need to fix it")
        ext_id, url = _mock_jira(item)
        assert ext_id.startswith("ENG-")
        assert "atlassian.net/browse/ENG-" in url


class TestSchedulerAgent:
    """Tests for the scheduler agent."""

    @pytest.mark.unit
    def test_skips_when_no_follow_up_needed(self, state_with_summary):
        from backend.agents.scheduler import scheduler_agent
        no_followup = state_with_summary.model_copy(update={
            "summary": state_with_summary.summary.model_copy(update={"follow_up_needed": False})
        })
        result = scheduler_agent(no_followup)
        assert result.get("follow_up_event") is None
        assert "scheduling" in result.get("completed_stages", [])

    @pytest.mark.unit
    def test_skips_when_no_summary(self, sample_state):
        from backend.agents.scheduler import scheduler_agent
        result = scheduler_agent(sample_state)
        assert result.get("follow_up_event") is None

    @pytest.mark.unit
    def test_gcal_url_format(self):
        from backend.agents.scheduler import _build_gcal_url
        event = CalendarEvent(
            title="Follow-up: Resolve blockers",
            start_datetime="2026-04-01T10:00:00",
            end_datetime="2026-04-01T10:30:00",
            attendees=["alice@co.com", "bob@co.com"],
            description="Resolve payment provider and staging issues",
        )
        url = _build_gcal_url(event, ["alice@co.com"])
        assert url.startswith("https://calendar.google.com/calendar/render")
        assert "Follow-up" in url


class TestMemoryAgent:
    """Tests for the memory agent using mock store."""

    @pytest.mark.unit
    def test_returns_empty_when_no_summary(self, sample_state):
        from backend.agents.memory import memory_agent
        result = memory_agent(sample_state)
        assert result["recurring_issues"] == []

    @pytest.mark.unit
    def test_detects_recurring_issue(self, state_with_summary):
        from backend.agents.memory import _mock_store, _mock_upsert, _mock_check, memory_agent

        # Seed the store with a past meeting having the same blocker
        _mock_store.clear()
        _mock_store.append({
            "meeting_id": "past-meeting-000",
            "text": "Payment provider decision still pending",
            "date": "2026-03-01",
        })

        result = memory_agent(state_with_summary)
        # Should detect "payment provider" as recurring
        assert any("payment" in r.lower() or "provider" in r.lower()
                   for r in result["recurring_issues"])
        _mock_store.clear()


class TestStateSchema:
    """Tests that the Pydantic state schema validates correctly."""

    @pytest.mark.unit
    def test_default_state_is_valid(self):
        state = MeetingState(meeting_id="abc-123")
        assert state.meeting_id == "abc-123"
        assert state.action_items == []
        assert state.graph_errors == []
        assert state.current_stage == "pending"

    @pytest.mark.unit
    def test_action_item_priority_validation(self):
        with pytest.raises(Exception):
            ActionItem(title="t", owner_name="n", priority="critical", source_quote="q")

    @pytest.mark.unit
    def test_meeting_summary_follow_up_default(self):
        summary = MeetingSummary(
            goal="Test goal",
            decisions=[],
            blockers=[],
        )
        assert summary.follow_up_needed is False


class TestDistributionAgent:
    """Tests for the distribution agent output."""

    @pytest.mark.unit
    def test_email_contains_goal(self, state_with_actions):
        from backend.agents.distribution import _generate_email
        html = _generate_email(state_with_actions)
        assert state_with_actions.summary.goal in html

    @pytest.mark.unit
    def test_email_contains_action_items(self, state_with_actions):
        from backend.agents.distribution import _generate_email
        # Route the tasks first
        state_with_actions = state_with_actions.model_copy(update={
            "routed_tasks": [
                RoutedTask(
                    action_item=state_with_actions.action_items[0],
                    tool="jira",
                    external_id="ENG-1234",
                    url="https://your-org.atlassian.net/browse/ENG-1234"
                )
            ]
        })
        html = _generate_email(state_with_actions)
        assert "ENG-1234" in html or "Jira" in html

    @pytest.mark.unit
    def test_slack_brief_contains_decisions(self, state_with_actions):
        from backend.agents.distribution import _generate_slack_brief
        brief = _generate_slack_brief(state_with_actions)
        assert "Decisions" in brief
        assert len(brief) > 100

    @pytest.mark.unit
    def test_handles_missing_summary(self, sample_state):
        from backend.agents.distribution import _generate_email, _generate_slack_brief
        email = _generate_email(sample_state)
        slack = _generate_slack_brief(sample_state)
        assert isinstance(email, str)
        assert isinstance(slack, str)


# ══════════════════════════════════════════════════════════════════════════════
# Integration test — calls real Claude API (marked separately)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.api
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
def test_full_graph_text_input():
    """End-to-end test: paste transcript → full graph run → results."""
    from backend.graph.graph import run_meeting_graph

    state = MeetingState(
        meeting_id="integration-test-001",
        meeting_title="Integration Test Meeting",
        attendees=["alice@test.com", "bob@test.com"],
        transcript_text="""Alice: We need to fix the login bug by Friday. It's blocking customers.
Bob: I'll handle that. Should take a day. 
Alice: Also, we've decided to move the launch date to April 15th.
Bob: Got it. I'll update the roadmap doc too.
Alice: Great. One blocker — we need design approval before we can finalize the UI.""",
    )

    result = run_meeting_graph(state)

    # Check summary was generated
    assert result.summary is not None
    assert len(result.summary.goal) > 10
    assert len(result.summary.decisions) >= 1

    # Check action items extracted
    assert len(result.action_items) >= 1

    # Check routing ran
    assert len(result.routed_tasks) >= 1
    assert all(t.tool in ["jira","asana","linear","notion","calendar","unrouted"]
               for t in result.routed_tasks)

    # Check no crash errors
    critical_errors = [e for e in result.graph_errors if "TranscriptionAgent" in e or "SummaryAgent" in e]
    assert critical_errors == [], f"Critical errors: {critical_errors}"

    print(f"\n✅ Integration test passed:")
    print(f"   Goal: {result.summary.goal}")
    print(f"   Decisions: {len(result.summary.decisions)}")
    print(f"   Blockers: {len(result.summary.blockers)}")
    print(f"   Action items: {len(result.action_items)}")
    print(f"   Routed tasks: {len(result.routed_tasks)}")
    print(f"   Errors: {result.graph_errors}")
