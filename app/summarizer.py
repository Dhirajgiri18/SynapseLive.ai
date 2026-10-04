from datetime import datetime
from pathlib import Path

from app import llm
from app.state import MeetingState
from config import NOTES_DIR


def summarize_and_save(state: MeetingState, notes_dir: str | Path = NOTES_DIR) -> Path:
    transcript = state.transcript_text()
    if not transcript:
        raise ValueError("There is no transcript to save yet.")

    prompt = f"""Summarize this meeting transcript for a project team.
Include a short overview, decisions, action items with owners when stated, and open questions.
Do not invent details. Use concise Markdown.

Transcript:
{transcript}
"""
    try:
        summary = llm.generate(prompt)
    except Exception as error:
        summary = f"Summary generation unavailable: {error}\n\nThe full transcript is included below."

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(notes_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"meeting_{timestamp}.md"
    output_path.write_text(
        f"# Meeting Notes - {datetime.now():%Y-%m-%d %H:%M}\n\n"
        f"## Summary\n\n{summary}\n\n"
        f"## Transcript\n\n{transcript}\n",
        encoding="utf-8",
    )
    return output_path
