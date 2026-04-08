# Browser Task Workflow

## Purpose
Execute arbitrary browser automation tasks using AI-driven navigation.

## Steps

### 1. Task Input
- Receive natural language task description
- Optional: starting URL
- Optional: max navigation steps

### 2. Intent Classification
- Parse task to identify target platform
- If no platform detected, use generic browser handler

### 3. Browser Initialization
- Launch Playwright browser (headless or headed)
- Create new browser context with stealth scripts

### 4. Navigation Loop
Repeat until goal achieved or max_steps reached:

1. **Capture Screenshot** - Take screenshot of current page state
2. **Vision Analysis** - Send screenshot to NVIDIA Vision model with goal
3. **Action Determination** - Parse LLM response to determine next action
4. **Action Execution** - Execute atomic browser action (click, fill, scroll, etc.)
5. **Human-like Delay** - Add random delay between actions (optional)

### 5. Content Extraction
- Extract final page content
- Optionally take final screenshot

### 6. Result Formatting
- Format output as Markdown or JSON
- Save to session history

### 7. Cleanup
- Close browser context
- Release resources

## Example Tasks
- "Search YouTube for Python tutorials and extract top 5 video titles"
- "Open LinkedIn and find posts about AI from the last week"
- "Navigate to twitter.com and search for #machinelearning"

## Error Handling
- Navigation timeout: retry with exponential backoff
- Element not found: try alternative selectors
- CAPTCHA encountered: notify user, allow manual bypass
- Rate limiting: wait and retry

## Success Criteria
- Task description fulfilled
- Output extracted in requested format
- Session history updated
