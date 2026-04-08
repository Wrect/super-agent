// Omni Browser Agent Dashboard JavaScript

const API_BASE = window.location.origin;
let ws = null;
let currentTaskId = null;

// Initialize WebSocket connection
function initWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws/tasks/${currentTaskId}`);
    
    ws.onopen = () => {
        updateConnectionStatus(true);
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onclose = () => {
        updateConnectionStatus(false);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus(false);
    };
}

function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connectionStatus');
    const dot = statusEl.querySelector('.dot');
    
    if (connected) {
        statusEl.innerHTML = '<span class="dot"></span>Connected';
        statusEl.classList.add('connected');
    } else {
        statusEl.innerHTML = '<span class="dot"></span>Disconnected';
        statusEl.classList.remove('connected');
    }
}

function handleWebSocketMessage(data) {
    const outputEl = document.getElementById('outputContent');
    const statusEl = document.getElementById('currentTaskStatus');
    const progressEl = document.getElementById('taskProgress');
    
    progressEl.style.display = 'block';
    
    if (data.status) {
        statusEl.textContent = data.status;
        updateTimeline(data.status);
    }
    
    if (data.output) {
        outputEl.textContent = formatOutput(data.output);
    }
    
    if (data.error) {
        outputEl.textContent = `Error: ${data.error}`;
    }
}

function updateTimeline(status) {
    const steps = document.querySelectorAll('.timeline-step');
    let stepIndex = 0;
    
    switch (status) {
        case 'pending':
            stepIndex = 0;
            break;
        case 'running':
            stepIndex = 1;
            break;
        case 'processing':
            stepIndex = 2;
            break;
        case 'completed':
            stepIndex = 3;
            break;
        case 'failed':
            stepIndex = 3;
            break;
    }
    
    steps.forEach((step, index) => {
        if (index <= stepIndex) {
            step.classList.add('active');
        } else {
            step.classList.remove('active');
        }
    });
}

function formatOutput(output) {
    if (typeof output === 'object') {
        return JSON.stringify(output, null, 2);
    }
    return output;
}

// Task submission
document.getElementById('taskForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const taskInput = document.getElementById('taskInput');
    const headlessMode = document.getElementById('headlessMode');
    const submitBtn = document.getElementById('submitBtn');
    const outputEl = document.getElementById('outputContent');
    const progressEl = document.getElementById('taskProgress');
    
    const taskDescription = taskInput.value.trim();
    if (!taskDescription) {
        alert('Please enter a task description');
        return;
    }
    
    submitBtn.disabled = true;
    submitBtn.querySelector('.btn-text').style.display = 'none';
    submitBtn.querySelector('.btn-loading').style.display = 'inline';
    
    progressEl.style.display = 'block';
    outputEl.textContent = 'Submitting task...';
    
    try {
        const response = await fetch('/task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                description: taskDescription,
                headless: headlessMode.checked
            })
        });
        
        const data = await response.json();
        
        if (data.task_id) {
            currentTaskId = data.task_id;
            document.getElementById('currentTaskId').textContent = data.task_id;
            outputEl.textContent = 'Task submitted. Waiting for execution...';
            
            // Connect WebSocket for live updates
            initWebSocket();
        } else {
            outputEl.textContent = `Error: ${data.error || 'Unknown error'}`;
        }
        
    } catch (error) {
        outputEl.textContent = `Error: ${error.message}`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.querySelector('.btn-text').style.display = 'inline';
        submitBtn.querySelector('.btn-loading').style.display = 'none';
    }
});

// Debate engine
document.getElementById('debateBtn').addEventListener('click', async () => {
    const promptA = document.getElementById('promptA').value.trim();
    const promptB = document.getElementById('promptB').value.trim();
    const resultEl = document.getElementById('debateResult');
    const outputEl = document.getElementById('debateOutput');
    
    if (!promptA || !promptB) {
        alert('Please enter both prompts');
        return;
    }
    
    resultEl.style.display = 'block';
    outputEl.textContent = 'Synthesizing prompts...';
    
    try {
        const response = await fetch('/debate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt_a: promptA,
                prompt_b: promptB
            })
        });
        
        const data = await response.json();
        
        if (data.synthesized_prompt) {
            outputEl.innerHTML = `
                <div class="synthesized-prompt">
                    <strong>Synthesized:</strong> ${data.synthesized_prompt}
                </div>
                <div class="explanation">
                    <strong>Explanation:</strong> ${data.explanation}
                </div>
                <div class="confidence">
                    <strong>Confidence:</strong> ${(data.confidence * 100).toFixed(1)}%
                </div>
                ${data.dropped_constraints && data.dropped_constraints.length > 0 ? `
                    <div class="dropped">
                        <strong>Dropped Constraints:</strong>
                        <ul>
                            ${data.dropped_constraints.map(c => `<li>${c}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            `;
        } else {
            outputEl.textContent = `Error: ${data.error || 'Unknown error'}`;
        }
        
    } catch (error) {
        outputEl.textContent = `Error: ${error.message}`;
    }
});

// Refresh history
document.getElementById('refreshHistory').addEventListener('click', async () => {
    const historyList = document.getElementById('historyList');
    
    try {
        const response = await fetch('/history');
        const data = await response.json();
        
        if (data.history && data.history.length > 0) {
            historyList.innerHTML = data.history.map(entry => `
                <div class="history-item">
                    <div class="history-id">${entry.id}</div>
                    <div class="history-task">${entry.task.description}</div>
                    <div class="history-status ${entry.result.status}">${entry.result.status}</div>
                </div>
            `).join('');
        } else {
            historyList.innerHTML = '<div class="empty-state">No tasks executed yet.</div>';
        }
        
    } catch (error) {
        historyList.innerHTML = `<div class="error">Error loading history: ${error.message}</div>`;
    }
});

// Load platform status
async function loadPlatformStatus() {
    try {
        const response = await fetch('/auth/status');
        const data = await response.json();
        
        const platforms = ['youtube', 'instagram', 'linkedin', 'twitter'];
        platforms.forEach(platform => {
            const card = document.querySelector(`[data-platform="${platform}"]`);
            if (card && data[platform]) {
                const statusEl = card.querySelector('.platform-status');
                if (data[platform].authenticated) {
                    statusEl.textContent = 'Authenticated';
                    card.classList.add('authenticated');
                } else if (data[platform].demo_mode) {
                    statusEl.textContent = 'Demo Mode';
                    card.classList.add('demo');
                } else {
                    statusEl.textContent = 'Not Authenticated';
                    card.classList.add('unauthenticated');
                }
            }
        });
        
    } catch (error) {
        console.error('Error loading platform status:', error);
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    loadPlatformStatus();
    document.getElementById('refreshHistory').click();
});