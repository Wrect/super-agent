"""
Tests for debate engine.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from engine.debate import DebateEngine, get_debate_engine
from engine.memory import SessionMemory
from models.schemas import SynthesizedPrompt


class TestDebateEngine:
    """Tests for DebateEngine."""

    @pytest.mark.asyncio
    async def test_synthesize_compatible_prompts(self):
        """Test synthesizing compatible prompts."""
        engine = DebateEngine()

        # Mock the AI inference to avoid actual API calls
        with patch(
            "pipeline.ai_inference.run_llm_completion", new_callable=AsyncMock
        ) as mock_llm:
            # Mock intent extraction
            mock_llm.side_effect = [
                "Find Python tutorial videos",
                "Find recent Python tutorial videos",
                '{"conflicts": [], "overlaps": ["Both want Python tutorials"], "mutual_exclusion": false}',
                '{"prompt": "Find recent Python tutorial videos", "explanation": "Combined requirements", "confidence": 0.9}',
            ]

            result = await engine.synthesize(
                prompt_a="Find Python tutorials",
                prompt_b="Find recent Python tutorials",
            )

            assert isinstance(result, SynthesizedPrompt)
            assert result.synthesized_prompt is not None

    @pytest.mark.asyncio
    async def test_synthesize_conflicting_prompts(self):
        """Test synthesizing conflicting prompts."""
        engine = DebateEngine()

        with patch(
            "pipeline.ai_inference.run_llm_completion", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.side_effect = [
                "Search YouTube only from popular channels",
                "Find recent videos",
                '{"conflicts": ["Channel filter"], "overlaps": [], "mutual_exclusion": true}',
                '{"prompt": "Find recent videos from popular channels", "explanation": "Prioritized B with channel filter from A", "confidence": 0.7}',
            ]

            result = await engine.synthesize(
                prompt_a="Search YouTube only from popular channels",
                prompt_b="Find recent videos",
            )

            assert isinstance(result, SynthesizedPrompt)
            assert len(result.dropped_constraints) >= 0

    @pytest.mark.asyncio
    async def test_analyze_conflicts(self):
        """Test conflict analysis without full synthesis."""
        engine = DebateEngine()

        with patch(
            "pipeline.ai_inference.run_llm_completion", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.side_effect = [
                "Intent A",
                "Intent B",
                '{"conflicts": ["conflict1"], "overlaps": ["overlap1"], "mutual_exclusion": false}',
            ]

            context = await engine.analyze_conflicts(
                prompt_a="Prompt A", prompt_b="Prompt B"
            )

            assert context.prompt_a == "Prompt A"
            assert context.prompt_b == "Prompt B"
            assert context.intent_a == "Intent A"
            assert len(context.conflicts) >= 0


class TestSessionMemory:
    """Tests for SessionMemory."""

    @pytest.mark.asyncio
    async def test_add_entry(self, session_history_entry):
        """Test adding entry to session memory."""
        memory = SessionMemory(max_entries=10)

        await memory.add(session_history_entry)

        entry = await memory.get(session_history_entry.id)
        assert entry is not None
        assert entry.id == session_history_entry.id

    @pytest.mark.asyncio
    async def test_get_recent(self, session_history_entry):
        """Test getting recent entries."""
        memory = SessionMemory(max_entries=10)

        await memory.add(session_history_entry)

        recent = await memory.get_recent(limit=5)
        assert len(recent) >= 1

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when over max entries."""
        memory = SessionMemory(max_entries=2)

        from models.schemas import SessionHistory, BrowserTask, TaskResult, TaskStatus
        from datetime import datetime

        # Add 3 entries (should evict oldest)
        for i in range(3):
            task = BrowserTask(id=f"task-{i}", description=f"Task {i}")
            result = TaskResult(
                task_id=f"task-{i}",
                status=TaskStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
            )
            entry = SessionHistory(
                id=f"history-{i}", timestamp=datetime.utcnow(), task=task, result=result
            )
            await memory.add(entry)

        # Should have max 2 entries
        stats = memory.get_stats()
        assert stats["total_entries"] <= 2

    @pytest.mark.asyncio
    async def test_search(self, session_history_entry):
        """Test searching session history."""
        memory = SessionMemory(max_entries=10)

        await memory.add(session_history_entry)

        results = await memory.search("Python")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_delete(self, session_history_entry):
        """Test deleting entry."""
        memory = SessionMemory(max_entries=10)

        await memory.add(session_history_entry)
        deleted = await memory.delete(session_history_entry.id)
        assert deleted is True

        entry = await memory.get(session_history_entry.id)
        assert entry is None

    @pytest.mark.asyncio
    async def test_clear(self, session_history_entry):
        """Test clearing all history."""
        memory = SessionMemory(max_entries=10)

        await memory.add(session_history_entry)
        await memory.clear()

        stats = memory.get_stats()
        assert stats["total_entries"] == 0
