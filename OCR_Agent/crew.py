"""crew.py — CrewAI Crew assembly for Project Omni-Extract.

Provides a factory function that wires the agent and task together into a
single-agent Crew.  This module is consumed by ``interface.py`` and should
NOT be executed directly.
"""

from __future__ import annotations

from crewai import Crew, Process

from agents import build_omni_extractor_agent
from tasks import build_extraction_task


def build_extraction_crew(file_path: str) -> Crew:
    """Assemble and return the Omni-OCR extraction crew.

    Args:
        file_path: Absolute path to the file to process.

    Returns:
        A ``Crew`` ready to be kicked off with ``.kickoff()``.
    """
    agent = build_omni_extractor_agent()
    task = build_extraction_task(agent=agent, file_path=file_path)

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
