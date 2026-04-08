"""agents.py — CrewAI Agent definition for the Omni-OCR Sub-Agent.

Defines the ``OmniExtractor`` agent whose sole purpose is to receive a file
path, select the appropriate NVIDIA extraction tool based on file type, run it,
and return a Pydantic-validated ``ExtractionResult``.

All model IDs, role strings, and behavioural settings come from ``config.yaml``
via ``config.py``.
"""

from __future__ import annotations

import os

from crewai import Agent, LLM

from config import API, MODELS, LLM_PARAMS, AGENT_CFG
from tools import (
    AudioTranscriptionTool,
    VideoExtractionTool,
    VisionOCRTool,
)
from vision_analyzer import VisionUnderstandingTool


# ---------------------------------------------------------------------------
# LLM Configuration
# ---------------------------------------------------------------------------

def _build_nvidia_llm() -> LLM:
    """Construct a CrewAI-compatible LLM instance pointing at the NVIDIA
    API Catalog.

    Returns:
        A ``LLM`` configured with the model from ``config.MODELS.agent_llm``.
    """
    api_key = API.api_key

    # litellm's OpenAI provider reads OPENAI_API_KEY from the environment
    # rather than honouring the api_key constructor param.  Bridge it here.
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    return LLM(
        model=MODELS.agent_llm,
        base_url=API.base_url,
        api_key=api_key,
        temperature=LLM_PARAMS.temperature,
        max_tokens=LLM_PARAMS.max_tokens,
    )


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

def build_omni_extractor_agent() -> Agent:
    """Create and return the ``OmniExtractor`` CrewAI agent.

    The agent is equipped with four tools covering images/documents (OCR +
    understanding), audio, and video.  It is instructed to autonomously
    select the correct tool based on file extension and format its output
    to match the ``ExtractionResult`` Pydantic schema exactly.

    Returns:
        A fully configured ``Agent`` instance.
    """
    llm = _build_nvidia_llm()

    return Agent(
        role=AGENT_CFG.role,
        goal=AGENT_CFG.goal,
        backstory=AGENT_CFG.backstory,
        tools=[
            VisionOCRTool(),
            VisionUnderstandingTool(),
            AudioTranscriptionTool(),
            VideoExtractionTool(),
        ],
        llm=llm,
        verbose=AGENT_CFG.verbose,
        allow_delegation=AGENT_CFG.allow_delegation,
        max_iter=AGENT_CFG.max_iter,
    )
