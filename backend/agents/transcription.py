"""
TranscriptionAgent
──────────────────
Converts an audio file to a diarized transcript using:
  - OpenAI Whisper API  (speech-to-text)
  - Simple speaker turn detection from Whisper segments

For production, replace speaker detection with pyannote.audio 3.0.
"""

import os
import re
import logging
from pathlib import Path
from openai import OpenAI
from ..models.schemas import MeetingState, Turn

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def transcription_agent(state: MeetingState) -> dict:
    """
    LangGraph node. Reads: audio_path OR transcript_text.
    Writes: transcript (List[Turn]), current_stage, completed_stages.
    """
    logger.info(f"[TranscriptionAgent] Starting for meeting {state.meeting_id}")

    try:
        # ── Path A: raw text was pasted in — parse into fake turns ───────────
        if state.transcript_text and not state.audio_path:
            turns = _parse_text_transcript(state.transcript_text)
            return {
                "transcript": turns,
            }

        # ── Path B: audio file — call Whisper ─────────────────────────────────
        if not state.audio_path:
            raise ValueError("Neither audio_path nor transcript_text provided.")

        audio_path = Path(state.audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"[TranscriptionAgent] Calling Whisper on {audio_path.name}")

        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",    # returns segments with timestamps
                timestamp_granularities=["segment"],
            )

        turns = _whisper_segments_to_turns(response)

        logger.info(f"[TranscriptionAgent] Produced {len(turns)} turns")

        return {
            "transcript": turns,
        }

    except Exception as e:
        logger.error(f"[TranscriptionAgent] Error: {e}")
        return {
            "graph_errors": state.graph_errors + [f"TranscriptionAgent: {e}"],
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _whisper_segments_to_turns(response) -> list[Turn]:
    """
    Groups Whisper verbose_json segments into speaker turns.
    Uses dot-notation (seg.start) because the OpenAI SDK returns
    TranscriptionSegment objects, not plain dicts.
    """
    segments = response.segments or []
    if not segments:
        return [Turn(
            speaker="SPEAKER_00",
            text=response.text.strip(),
            start_ms=0,
            end_ms=0,
        )]

    turns: list[Turn] = []
    PAUSE_THRESHOLD = 1.5
    speaker_idx = 0
    buffer_text = []
    buffer_start = int(segments[0].start * 1000)
    prev_end = segments[0].end

    for seg in segments:
        gap = seg.start - prev_end
        if gap > PAUSE_THRESHOLD and buffer_text:
            turns.append(Turn(
                speaker=f"SPEAKER_{speaker_idx:02d}",
                text=" ".join(buffer_text).strip(),
                start_ms=buffer_start,
                end_ms=int(prev_end * 1000),
            ))
            speaker_idx = (speaker_idx + 1) % 4
            buffer_text = []
            buffer_start = int(seg.start * 1000)

        buffer_text.append(seg.text.strip())
        prev_end = seg.end

    if buffer_text:
        turns.append(Turn(
            speaker=f"SPEAKER_{speaker_idx:02d}",
            text=" ".join(buffer_text).strip(),
            start_ms=buffer_start,
            end_ms=int(prev_end * 1000),
        ))

    return turns


def _parse_text_transcript(raw: str) -> list[Turn]:
    """
    Parses pasted transcripts in two common formats:

    Format A (Speaker-labeled):
        Alice: We need to ship by Friday.
        Bob: I agree, but the API isn't ready.

    Format B (Plain text — no speaker labels):
        We need to ship by Friday.
        I agree, but the API isn't ready.
    """
    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]

    # Detect Format A: lines starting with "Name: text"
    speaker_pattern = re.compile(r"^([A-Za-z][A-Za-z0-9 ]{0,30}):\s+(.+)$")
    labeled = [speaker_pattern.match(l) for l in lines]

    if any(labeled):
        turns = []
        for i, (line, match) in enumerate(zip(lines, labeled)):
            if match:
                turns.append(Turn(
                    speaker=match.group(1).strip(),
                    text=match.group(2).strip(),
                    start_ms=i * 5000,      # fake 5-second offsets
                    end_ms=(i + 1) * 5000,
                ))
            else:
                # Continuation line — append to last turn
                if turns:
                    turns[-1] = turns[-1].model_copy(
                        update={"text": turns[-1].text + " " + line}
                    )
        return turns

    # Format B — group every 3 lines into a pseudo-turn, alternating speakers
    turns = []
    chunk: list[str] = []
    speaker_idx = 0
    for i, line in enumerate(lines):
        chunk.append(line)
        if len(chunk) == 3 or i == len(lines) - 1:
            turns.append(Turn(
                speaker=f"SPEAKER_{speaker_idx:02d}",
                text=" ".join(chunk),
                start_ms=len(turns) * 8000,
                end_ms=(len(turns) + 1) * 8000,
            ))
            speaker_idx = (speaker_idx + 1) % 4
            chunk = []

    return turns
