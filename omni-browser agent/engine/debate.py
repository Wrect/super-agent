"""
Prompt History & Debate Engine for Omni Browser Agent.
Implements 3-step prompt synthesis: Intent Analysis, Chain-of-Thought Debate, and Synthesis.
"""

import asyncio
from typing import Dict, Any, List, Optional

from core.logger import get_component_logger
from core.config import get_settings
from core.exceptions import DebateResolutionError
from models.schemas import DebateContext, SynthesizedPrompt
from pipeline.ai_inference import run_llm_completion


class DebateEngine:
    """
    3-Step Prompt Synthesis Engine.

    1. Intent Analysis: Extract intent from both prompts
    2. Chain-of-Thought Debate: LLM internal debate identifying conflicts & overlaps
    3. Synthesis: Generate unified prompt, prioritizing B if mutually exclusive
    """

    def __init__(self):
        self.logger = get_component_logger("debate")
        self.settings = get_settings()
        self.temperature = self.settings.debate.debate_temperature
        self.max_tokens = self.settings.debate.debate_max_tokens

    async def synthesize(self, prompt_a: str, prompt_b: str) -> SynthesizedPrompt:
        """
        Synthesize two prompts into a unified prompt.

        Args:
            prompt_a: Historical/previous prompt
            prompt_b: New/current prompt

        Returns:
            SynthesizedPrompt with unified prompt and explanation
        """
        self.logger.info(
            f"Synthesizing prompts: A='{prompt_a[:50]}...' vs B='{prompt_b[:50]}...'"
        )

        # Step 1: Intent Analysis
        intent_a = await self._extract_intent(prompt_a, "A")
        intent_b = await self._extract_intent(prompt_b, "B")

        self.logger.debug(f"Intent A: {intent_a}")
        self.logger.debug(f"Intent B: {intent_b}")

        # Step 2: Chain-of-Thought Debate
        debate_result = await self._run_debate(intent_a, intent_b, prompt_a, prompt_b)

        conflicts = debate_result.get("conflicts", [])
        overlaps = debate_result.get("overlaps", [])

        self.logger.debug(f"Conflicts: {conflicts}")
        self.logger.debug(f"Overlaps: {overlaps}")

        # Step 3: Synthesis
        synthesis_result = await self._synthesize_prompt(
            prompt_a, prompt_b, intent_a, intent_b, conflicts, overlaps
        )

        dropped_constraints = conflicts  # Conflicts become dropped constraints

        return SynthesizedPrompt(
            original_prompt_a=prompt_a,
            original_prompt_b=prompt_b,
            synthesized_prompt=synthesis_result["prompt"],
            explanation=synthesis_result["explanation"],
            dropped_constraints=dropped_constraints,
            confidence=synthesis_result.get("confidence", 0.8),
        )

    async def _extract_intent(self, prompt: str, label: str) -> str:
        """Extract intent from a prompt."""
        messages = [
            {
                "role": "system",
                "content": "You are an intent extraction system. Extract the core intent from the user's prompt. Focus on what they want to accomplish, not how they want it done.",
            },
            {
                "role": "user",
                "content": f"""Extract the core intent from this prompt (label: {label}):

{prompt}

Provide a one-sentence summary of the intent.""",
            },
        ]

        try:
            result = await run_llm_completion(
                messages=messages, temperature=self.temperature, max_tokens=200
            )
            return result.strip()
        except Exception as e:
            self.logger.warning(f"Intent extraction failed: {e}")
            return prompt[:100]  # Fallback to truncated prompt

    async def _run_debate(
        self, intent_a: str, intent_b: str, prompt_a: str, prompt_b: str
    ) -> Dict[str, Any]:
        """Run chain-of-thought debate between two intents."""
        messages = [
            {
                "role": "system",
                "content": """You are a debate system that analyzes two prompts to find conflicts and overlaps. 
Respond with a JSON object containing:
- conflicts: List of mutually exclusive requirements between prompts
- overlaps: List of common/shared requirements
- mutual_exclusion: Boolean indicating if prompts are mutually exclusive""",
            },
            {
                "role": "user",
                "content": f"""Analyze these two prompts:

Prompt A: {prompt_a}
Intent A: {intent_a}

Prompt B: {prompt_b}
Intent B: {intent_b}

Identify:
1. Conflicts (requirements that cannot both be satisfied)
2. Overlaps (requirements that are shared)

Respond in JSON format.""",
            },
        ]

        try:
            result = await run_llm_completion(
                messages=messages, temperature=self.temperature, max_tokens=500
            )

            # Parse JSON from result
            import json
            import re

            # Try to extract JSON from response
            json_match = re.search(r"\{[^{}]*\}", result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # Try parsing entire response
            return json.loads(result)

        except Exception as e:
            self.logger.warning(f"Debate failed: {e}")
            return {"conflicts": [], "overlaps": [], "mutual_exclusion": False}

    async def _synthesize_prompt(
        self,
        prompt_a: str,
        prompt_b: str,
        intent_a: str,
        intent_b: str,
        conflicts: List[str],
        overlaps: List[str],
    ) -> Dict[str, Any]:
        """Synthesize a unified prompt from two prompts."""
        priority = "B" if conflicts else "A"

        messages = [
            {
                "role": "system",
                "content": """You are a prompt synthesis system. Create a unified prompt that satisfies both input prompts when possible.

Rules:
- If prompts are compatible, merge them into a single coherent prompt
- If prompts conflict, prioritize the newer prompt (B) but note what was dropped
- Preserve all overlapping requirements
- Output a JSON object with the synthesized prompt and explanation""",
            },
            {
                "role": "user",
                "content": f"""Synthesize these prompts:

Prompt A (historical): {prompt_a}
Intent A: {intent_a}

Prompt B (new): {prompt_b}
Intent B: {intent_b}

Overlapping requirements: {overlaps}
Conflicting requirements: {conflicts}

Priority: {priority} (newer prompt wins conflicts)

Create a synthesized prompt that:
1. Satisfies all overlapping requirements
2. Resolves conflicts by prioritizing prompt B
3. Is clear and actionable

Respond in JSON format:
{{
    "prompt": "synthesized prompt",
    "explanation": "how conflicts were resolved",
    "confidence": 0.0-1.0
}}""",
            },
        ]

        try:
            result = await run_llm_completion(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            import json
            import re

            # Try to extract JSON
            json_match = re.search(r"\{[^{}]*\}", result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            return json.loads(result)

        except Exception as e:
            self.logger.warning(f"Synthesis failed: {e}")
            # Fallback: just return prompt B
            return {
                "prompt": prompt_b,
                "explanation": "Synthesis failed, defaulted to newer prompt",
                "confidence": 0.5,
            }

    async def analyze_conflicts(self, prompt_a: str, prompt_b: str) -> DebateContext:
        """
        Analyze conflicts between two prompts without full synthesis.

        Args:
            prompt_a: First prompt
            prompt_b: Second prompt

        Returns:
            DebateContext with analysis
        """
        intent_a = await self._extract_intent(prompt_a, "A")
        intent_b = await self._extract_intent(prompt_b, "B")

        debate_result = await self._run_debate(intent_a, intent_b, prompt_a, prompt_b)

        return DebateContext(
            prompt_a=prompt_a,
            prompt_b=prompt_b,
            intent_a=intent_a,
            intent_b=intent_b,
            conflicts=debate_result.get("conflicts", []),
            overlaps=debate_result.get("overlaps", []),
            priority_decision="B" if debate_result.get("mutual_exclusion") else "A",
        )


# Global debate engine instance
_debate_engine: Optional[DebateEngine] = None


def get_debate_engine() -> DebateEngine:
    """Get singleton debate engine instance."""
    global _debate_engine
    if _debate_engine is None:
        _debate_engine = DebateEngine()
    return _debate_engine
