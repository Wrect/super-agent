# Debate Synthesize Workflow

## Purpose
Synthesize two prompts into a unified prompt using the 3-step debate engine.

## When to Use
- User provides a new task that conflicts with a previous task
- Need to resolve priority between historical and new prompts
- Session history has accumulated constraints that may conflict

## 3-Step Process

### Step 1: Intent Analysis
Extract the core intent from each prompt.

**Input:**
- Prompt A: "Search for Python tutorials on YouTube, only from channels with 100k+ subscribers"
- Prompt B: "Find recent Python asyncio videos"

**LLM Prompt:**
```
Extract the core intent from this prompt. Focus on what they want to accomplish.

Prompt: {user_prompt}
Intent: {one sentence}
```

**Output:**
- Intent A: "Find Python tutorial videos from popular YouTube channels"
- Intent B: "Find recent Python asyncio tutorial videos"

### Step 2: Chain-of-Thought Debate
Identify conflicts and overlaps between intents.

**LLM Prompt:**
```
You are a debate system analyzing two prompts for conflicts and overlaps.

Prompt A Intent: {intent_a}
Prompt B Intent: {intent_b}

Respond with JSON:
{
  "conflicts": ["requirement that cannot be satisfied by both"],
  "overlaps": ["shared requirements"],
  "mutual_exclusion": true/false
}
```

**Output:**
```json
{
  "conflicts": [
    "Prompt A requires filtering by subscriber count, Prompt B doesn't specify"
  ],
  "overlaps": [
    "Both want Python tutorial videos from YouTube"
  ],
  "mutual_exclusion": false
}
```

### Step 3: Synthesis
Generate unified prompt, prioritizing newer prompt on conflicts.

**LLM Prompt:**
```
Synthesize these prompts into a single coherent prompt.

Historical Prompt (A): {prompt_a}
New Prompt (B): {prompt_b}

Overlapping requirements: {overlaps}
Conflicting requirements: {conflicts}
Priority: B (newer prompt wins on conflicts)

Rules:
- Merge overlapping requirements
- Resolve conflicts by prioritizing B
- Preserve any constraints unique to each prompt

Respond with JSON:
{
  "prompt": "synthesized prompt",
  "explanation": "how conflicts were resolved",
  "confidence": 0.0-1.0
}
```

**Output:**
```json
{
  "prompt": "Find recent Python asyncio tutorial videos from YouTube channels with 100k+ subscribers",
  "explanation": "Combined the channel filter from A with the recency and asyncio focus from B",
  "confidence": 0.85
}
```

## Decision Logic

### If Compatible (no conflicts)
- Merge both prompts into unified version
- Mark confidence as high (>0.8)

### If Mutually Exclusive
- Always prioritize the NEWER prompt (B)
- Document dropped constraints from A
- Mark confidence as medium (0.5-0.7)
- Optionally notify user about dropped requirements

### If Partial Overlap
- Merge overlapping parts
- Keep unique constraints from both
- Mark confidence based on complexity

## Output Format

```json
{
  "original_prompt_a": "...",
  "original_prompt_b": "...",
  "synthesized_prompt": "...",
  "explanation": "...",
  "dropped_constraints": ["..."],
  "confidence": 0.85
}
```

## Storage
- Save to session history as DebateContext
- Include in task metadata for future reference
