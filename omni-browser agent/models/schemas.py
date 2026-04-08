"""
Pydantic schemas for Omni Browser Agent.
Defines all input/output contracts for inter-component communication.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, HttpUrl


class Platform(str, Enum):
    """Supported social media platforms."""

    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    WEB = "web"


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BrowserTask(BaseModel):
    """Browser task definition."""

    id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="Natural language task description")
    platform: Optional[Platform] = Field(default=None, description="Target platform")
    url: Optional[HttpUrl] = Field(default=None, description="Starting URL")
    max_steps: int = Field(default=20, description="Maximum navigation steps")
    headless: bool = Field(default=True, description="Run browser in headless mode")
    extract_content: bool = Field(
        default=True, description="Extract content after task completion"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional task metadata"
    )


class TaskResult(BaseModel):
    """Result of task execution."""

    task_id: str = Field(..., description="Task identifier")
    status: TaskStatus = Field(..., description="Execution status")
    start_time: datetime = Field(..., description="Task start time")
    end_time: Optional[datetime] = Field(default=None, description="Task end time")
    output: Optional[Dict[str, Any]] = Field(
        default=None, description="Task output data"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    screenshots: List[str] = Field(
        default_factory=list, description="Paths to screenshots taken"
    )
    logs: List[str] = Field(
        default_factory=list, description="Log entries during execution"
    )


class PlatformPost(BaseModel):
    """Base model for social media posts."""

    platform: Platform
    post_id: str = Field(..., description="Unique post identifier")
    url: HttpUrl = Field(..., description="Post URL")
    timestamp: datetime = Field(..., description="Post creation timestamp")
    author: str = Field(..., description="Post author")
    content: str = Field(..., description="Post content/text")
    likes: int = Field(default=0, description="Number of likes/reactions")
    comments: int = Field(default=0, description="Number of comments")
    shares: int = Field(default=0, description="Number of shares")
    media_urls: List[HttpUrl] = Field(
        default_factory=list, description="Media attachments"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific metadata"
    )


class YouTubeVideo(PlatformPost):
    """YouTube video-specific model."""

    platform: Platform = Platform.YOUTUBE
    title: str = Field(..., description="Video title")
    duration: int = Field(..., description="Video duration in seconds")
    view_count: int = Field(default=0, description="View count")
    transcript: Optional[str] = Field(default=None, description="Video transcript")
    chapters: List[Dict[str, Any]] = Field(
        default_factory=list, description="Video chapters"
    )
    tags: List[str] = Field(default_factory=list, description="Video tags")


class InstagramPost(PlatformPost):
    """Instagram post-specific model."""

    platform: Platform = Platform.INSTAGRAM
    caption: str = Field(..., description="Post caption")
    media_type: str = Field(..., description="Media type (image, video, carousel)")
    alt_text: Optional[str] = Field(
        default=None, description="Alt text for accessibility"
    )


class LinkedInPost(PlatformPost):
    """LinkedIn post-specific model."""

    platform: Platform = Platform.LINKEDIN
    post_type: str = Field(..., description="Post type (article, update, video)")
    company: Optional[str] = Field(
        default=None, description="Company name if applicable"
    )


class Tweet(PlatformPost):
    """Twitter/X post-specific model."""

    platform: Platform = Platform.TWITTER
    retweet_count: int = Field(default=0, description="Retweet count")
    quote_count: int = Field(default=0, description="Quote tweet count")
    reply_count: int = Field(default=0, description="Reply count")
    is_retweet: bool = Field(default=False, description="Whether this is a retweet")
    is_reply: bool = Field(default=False, description="Whether this is a reply")


class ExtractionResult(BaseModel):
    """Result of content extraction operation."""

    success: bool = Field(..., description="Whether extraction was successful")
    platform: Platform = Field(
        ..., description="Platform from which content was extracted"
    )
    posts: List[PlatformPost] = Field(
        default_factory=list, description="Extracted posts"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Extraction timestamp"
    )
    # Compatibility with OCR_Agent schema
    extracted_text: Optional[str] = Field(
        default=None, description="Raw extracted text"
    )
    confidence_score: float = Field(
        default=1.0, description="Confidence in extraction accuracy"
    )


class DebateContext(BaseModel):
    """Context for prompt history debate engine."""

    prompt_a: str = Field(..., description="Historical prompt")
    prompt_b: str = Field(..., description="New prompt")
    intent_a: str = Field(..., description="Extracted intent from prompt A")
    intent_b: str = Field(..., description="Extracted intent from prompt B")
    conflicts: List[str] = Field(
        default_factory=list, description="Identified conflicts"
    )
    overlaps: List[str] = Field(default_factory=list, description="Identified overlaps")
    synthesized_prompt: Optional[str] = Field(
        default=None, description="Synthesized unified prompt"
    )
    priority_decision: str = Field(
        default="B", description="Which prompt takes priority (A or B)"
    )


class SessionHistory(BaseModel):
    """Session history entry."""

    id: str = Field(..., description="Unique history entry ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Entry timestamp"
    )
    task: BrowserTask = Field(..., description="Associated browser task")
    result: TaskResult = Field(..., description="Task execution result")
    debate_context: Optional[DebateContext] = Field(
        default=None, description="Debate context if applicable"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class SynthesizedPrompt(BaseModel):
    """Result of prompt synthesis operation."""

    original_prompt_a: str = Field(..., description="Original historical prompt")
    original_prompt_b: str = Field(..., description="Original new prompt")
    synthesized_prompt: str = Field(..., description="Synthesized unified prompt")
    explanation: str = Field(..., description="Explanation of synthesis decisions")
    dropped_constraints: List[str] = Field(
        default_factory=list, description="Constraints dropped from prompt A"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in synthesis quality"
    )


class APIErrorEnvelope(BaseModel):
    """Standardized API error response."""

    error: bool = Field(True, description="Indicates this is an error response")
    error_code: str = Field(..., description="Machine-readable error code")
    error_message: str = Field(..., description="Human-readable error message")
    component: str = Field(..., description="Component where error occurred")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )
