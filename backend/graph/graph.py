"""
Meeting Co-pilot LangGraph
──────────────────────────
Defines the full 7-node stateful agent graph.

Graph flow:
                              ┌──────────────┐
                              │    START     │
                              └──────┬───────┘
                                     │
                         ┌───────────▼────────────┐
                         │   TranscriptionAgent    │
                         └───────────┬────────────┘
                                     │
                         ┌───────────▼────────────┐
                         │      SummaryAgent       │
                         └───────────┬────────────┘
                                     │
                         ┌───────────▼────────────┐
                         │  ActionExtractorAgent   │
                         └──────┬────────┬─────────┘
                    (parallel)  │        │  (parallel)
             ┌──────────────────┘        └─────────────────┐
             │                                              │
  ┌──────────▼──────────┐                      ┌───────────▼──────────┐
  │    RouterAgent      │                      │    MemoryAgent       │
  └──────────┬──────────┘                      └───────────┬──────────┘
             │                                              │
             │ (join — both must complete)                  │
             └────────────────┬─────────────────────────────┘
                              │
             ┌────────────────▼─────────────────┐
             │  follow_up_needed?                │
             │  yes → SchedulerAgent             │
             │  no  → DistributionAgent directly │
             └────────────────┬─────────────────┘
                              │
                  ┌───────────▼────────────┐
                  │   DistributionAgent    │
                  └───────────┬────────────┘
                              │
                           ┌──▼──┐
                           │ END │
                           └─────┘

Notes:
- RouterAgent and MemoryAgent run in parallel using a fan-out / fan-in pattern.
- The conditional edge after the join checks summary.follow_up_needed.
- All errors are collected into state.graph_errors and never swallowed.
- LangGraph checkpointing is enabled via MemorySaver for fault recovery.
"""

import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from ..models.schemas import MeetingState
from ..agents.transcription import transcription_agent
from ..agents.summary import summary_agent
from ..agents.action_extractor import action_extractor_agent
from ..agents.router import router_agent
from ..agents.scheduler import scheduler_agent
from ..agents.memory import memory_agent
from ..agents.distribution import distribution_agent

logger = logging.getLogger(__name__)


# ── State update reducer ──────────────────────────────────────────────────────
# LangGraph merges partial dicts returned by nodes into the full state.
# We use dict merging (default) — each node returns only the fields it touches.


# ── Conditional edge functions ────────────────────────────────────────────────

def should_schedule(state: MeetingState) -> str:
    """
    After Router + Memory join, decide whether to schedule a follow-up.
    """
    if state.summary and state.summary.follow_up_needed and state.attendees:
        logger.info("[Graph] Routing to SchedulerAgent (follow_up_needed=True)")
        return "scheduler"
    logger.info("[Graph] Routing directly to DistributionAgent (no follow-up needed)")
    return "distribution"


def has_action_items(state: MeetingState) -> str:
    """
    After ActionExtractor, decide whether to run Router + Memory in parallel
    or skip straight to Distribution.
    """
    if state.graph_errors and any("error" in e.lower() for e in state.graph_errors):
        return "error"
    return "parallel"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Constructs and compiles the LangGraph StateGraph.
    Returns a compiled graph ready for .invoke() or .stream().
    """
    # Use MemorySaver for in-process checkpointing (swap for SqliteSaver / RedisSaver in prod)
    checkpointer = MemorySaver()

    builder = StateGraph(MeetingState)

    # ── Register nodes ────────────────────────────────────────────────────────
    builder.add_node("transcription",    transcription_agent)
    builder.add_node("summary",          summary_agent)
    builder.add_node("action_extractor", action_extractor_agent)
    builder.add_node("router",           router_agent)
    builder.add_node("memory",           memory_agent)
    builder.add_node("scheduler",        scheduler_agent)
    builder.add_node("distribution",     distribution_agent)

    # ── Sequential edges ──────────────────────────────────────────────────────
    builder.add_edge(START,              "transcription")
    builder.add_edge("transcription",    "summary")
    builder.add_edge("summary",          "action_extractor")

    # ── Sequential: router → memory → conditional branch ──────────────────────
    # Running sequentially avoids the INVALID_CONCURRENT_GRAPH_UPDATE error
    # that occurs when two parallel nodes both write to current_stage
    builder.add_edge("action_extractor", "router")
    builder.add_edge("router",           "memory")

    builder.add_conditional_edges(
        "memory",
        should_schedule,
        {"scheduler": "scheduler", "distribution": "distribution"},
    )

    builder.add_edge("scheduler",        "distribution")
    builder.add_edge("distribution",     END)

    return builder.compile(checkpointer=checkpointer)


# ── Singleton compiled graph ──────────────────────────────────────────────────
# Built once at import time so it's reused across requests.
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ── Run helper ────────────────────────────────────────────────────────────────

def run_meeting_graph(initial_state: MeetingState) -> MeetingState:
    """
    Runs the full graph synchronously and returns the final state.
    The thread_id enables checkpointing per meeting.
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": initial_state.meeting_id}}

    logger.info(f"[Graph] Starting graph for meeting {initial_state.meeting_id}")

    final_state_dict = graph.invoke(
        initial_state.model_dump(),
        config=config,
    )

    return MeetingState(**final_state_dict)


async def stream_meeting_graph(initial_state: MeetingState):
    """
    Async generator that streams state updates as the graph runs.
    Used by the /stream WebSocket endpoint.

    Yields dicts with: {"stage": str, "data": dict}
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": initial_state.meeting_id}}

    async for event in graph.astream(
        initial_state.model_dump(),
        config=config,
        stream_mode="updates",
    ):
        for node_name, state_update in event.items():
            stage = state_update.get("current_stage", node_name)
            yield {
                "stage": stage,
                "node": node_name,
                "data": state_update,
            }
