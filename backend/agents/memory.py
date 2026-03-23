"""
MemoryAgent
───────────
Detects recurring issues by comparing current blockers against past meetings
stored in Pinecone. Also upserts the current meeting into the store.

Two modes:
  MOCK  (PINECONE_API_KEY not set): uses in-memory store, always runs
  LIVE  (PINECONE_API_KEY set):     uses real Pinecone serverless index

Embedding model: text-embedding-3-small (OpenAI) — fast and cheap.
Similarity threshold: 0.82 (tune lower to surface more matches).
"""

import os
import json
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.82
EMBEDDING_MODEL = "text-embedding-3-small"
PINECONE_INDEX = os.environ.get("PINECONE_INDEX_NAME", "meeting-memory")

# In-memory fallback store (used when Pinecone is not configured)
_mock_store: list[dict] = []


def memory_agent(state) -> dict:
    """
    LangGraph node. Reads: summary (blockers), meeting_id.
    Writes: recurring_issues, current_stage, completed_stages.
    Runs in parallel with RouterAgent.
    """
    from ..models.schemas import MeetingState
    logger.info("[MemoryAgent] Checking for recurring issues")

    if not state.summary or not state.summary.blockers:
        return {
            "recurring_issues": [],
        }

    try:
        use_pinecone = bool(os.environ.get("PINECONE_API_KEY"))

        if use_pinecone:
            recurring = _pinecone_check(state)
        else:
            recurring = _mock_check(state)

        logger.info(f"[MemoryAgent] Found {len(recurring)} recurring issues")

        # Upsert current meeting into store for future retrieval
        if use_pinecone:
            _pinecone_upsert(state)
        else:
            _mock_upsert(state)

        return {
            "recurring_issues": recurring,
        }

    except Exception as e:
        logger.error(f"[MemoryAgent] Error: {e}")
        return {
            "graph_errors": state.graph_errors + [f"MemoryAgent: {e}"],
            "recurring_issues": [],
        }


# ── Pinecone path ─────────────────────────────────────────────────────────────

def _pinecone_check(state) -> list[str]:
    """Query Pinecone for blockers similar to current ones."""
    from openai import OpenAI
    from pinecone import Pinecone

    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(PINECONE_INDEX)

    recurring = []
    for blocker in state.summary.blockers:
        embedding = _embed(openai_client, blocker)
        results = index.query(
            vector=embedding,
            top_k=3,
            filter={"resolved": False, "meeting_id": {"$ne": state.meeting_id}},
            include_metadata=True,
        )
        for match in results.matches:
            if match.score >= SIMILARITY_THRESHOLD:
                prev_text = match.metadata.get("text", "unknown issue")
                recurring.append(
                    f'"{blocker}" — also raised on {match.metadata.get("date", "a previous meeting")}'
                )
                break

    return recurring


def _pinecone_upsert(state) -> None:
    """Store current meeting blockers in Pinecone."""
    from openai import OpenAI
    from pinecone import Pinecone

    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(PINECONE_INDEX)

    vectors = []
    for i, blocker in enumerate(state.summary.blockers):
        vec_id = hashlib.md5(f"{state.meeting_id}-blocker-{i}".encode()).hexdigest()
        vectors.append({
            "id": vec_id,
            "values": _embed(openai_client, blocker),
            "metadata": {
                "meeting_id": state.meeting_id,
                "text": blocker,
                "record_type": "blocker",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "resolved": False,
            },
        })

    if vectors:
        index.upsert(vectors=vectors)
        logger.info(f"[MemoryAgent] Upserted {len(vectors)} vectors to Pinecone")


def _embed(client, text: str) -> list[float]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


# ── Mock path (no Pinecone required) ─────────────────────────────────────────

def _mock_check(state) -> list[str]:
    """
    Simple keyword-based recurring issue detection against the in-memory store.
    Not semantic — just for demo purposes without Pinecone.
    """
    recurring = []
    for blocker in state.summary.blockers:
        blocker_words = set(blocker.lower().split())
        for past in _mock_store:
            if past["meeting_id"] == state.meeting_id:
                continue
            past_words = set(past["text"].lower().split())
            # Overlap > 40% of significant words = recurring
            stopwords = {"the", "a", "is", "to", "and", "or", "in", "of", "for", "with", "not"}
            b_sig = blocker_words - stopwords
            p_sig = past_words - stopwords
            if b_sig and len(b_sig & p_sig) / len(b_sig) > 0.4:
                recurring.append(
                    f'"{blocker}" — also raised on {past.get("date", "a previous meeting")}'
                )
                break

    return recurring


def _mock_upsert(state) -> None:
    """Append current blockers to the in-memory store."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    for blocker in state.summary.blockers:
        _mock_store.append({
            "meeting_id": state.meeting_id,
            "text": blocker,
            "date": date_str,
        })
