"""
Custom exception hierarchy for Omni Browser Agent.
Defines specific exceptions for different error types to enable precise error handling.
"""


class OmniBrowserError(Exception):
    """Base exception for all Omni Browser Agent errors."""

    def __init__(self, message: str, component: str = None):
        self.message = message
        self.component = component
        super().__init__(self.message)


class AuthExpiredError(OmniBrowserError):
    """Raised when authentication tokens or cookies have expired."""

    def __init__(self, platform: str, message: str = None):
        msg = message or f"Authentication expired for {platform}"
        super().__init__(msg, component="auth")
        self.platform = platform


class AgentAuthError(OmniBrowserError):
    """Raised when there's an error during the authentication process."""

    def __init__(self, platform: str, message: str = None):
        msg = message or f"Authentication failed for {platform}"
        super().__init__(msg, component="auth")
        self.platform = platform


class PlatformRateLimitError(OmniBrowserError):
    """Raised when a platform rate limit is exceeded."""

    def __init__(self, platform: str, retry_after: int = None):
        msg = f"Rate limit exceeded for {platform}"
        if retry_after:
            msg += f", retry after {retry_after} seconds"
        super().__init__(msg, component="pipeline")
        self.platform = platform
        self.retry_after = retry_after


class CaptchaBlockError(OmniBrowserError):
    """Raised when a CAPTCHA or similar bot detection mechanism is encountered."""

    def __init__(self, platform: str, message: str = None):
        msg = message or f"CAPTCHA encountered on {platform}"
        super().__init__(msg, component="browser")
        self.platform = platform


class BrowserLaunchError(OmniBrowserError):
    """Raised when there's an error launching or initializing the browser."""

    def __init__(self, browser_type: str, message: str = None):
        msg = message or f"Failed to launch {browser_type} browser"
        super().__init__(msg, component="browser")
        self.browser_type = browser_type


class NavigationTimeoutError(OmniBrowserError):
    """Raised when page navigation times out."""

    def __init__(self, url: str, timeout: int):
        super().__init__(
            f"Navigation to {url} timed out after {timeout}ms", component="browser"
        )
        self.url = url
        self.timeout = timeout


class ExtractionError(OmniBrowserError):
    """Base exception for content extraction errors."""

    def __init__(self, platform: str, message: str = None):
        msg = message or f"Extraction failed for {platform}"
        super().__init__(msg, component="pipeline")
        self.platform = platform


class TranscriptUnavailableError(ExtractionError):
    """Raised when transcript is unavailable for a video/audio."""

    def __init__(self, platform: str, content_id: str):
        super().__init__(
            platform, f"Transcript unavailable for {platform} content {content_id}"
        )
        self.content_id = content_id


class MediaDownloadError(ExtractionError):
    """Raised when media download fails."""

    def __init__(self, platform: str, content_id: str, message: str = None):
        msg = message or f"Media download failed for {platform} content {content_id}"
        super().__init__(platform, msg)
        self.content_id = content_id


class AudioProcessingError(ExtractionError):
    """Raised when audio processing fails."""

    def __init__(self, platform: str, message: str = None):
        msg = message or f"Audio processing failed for {platform}"
        super().__init__(platform, msg)


class DebateResolutionError(OmniBrowserError):
    """Raised when the debate engine cannot resolve conflicting prompts."""

    def __init__(self, prompt_a: str, prompt_b: str, message: str = None):
        msg = (
            message
            or f"Cannot resolve debate between prompts: '{prompt_a[:50]}...' vs '{prompt_b[:50]}...'"
        )
        super().__init__(msg, component="engine")
        self.prompt_a = prompt_a
        self.prompt_b = prompt_b


class PromptInjectionDetectedError(OmniBrowserError):
    """Raised when potential prompt injection is detected in scraped content."""

    def __init__(self, content: str, detected_pattern: str):
        super().__init__(
            f"Prompt injection detected: {detected_pattern}", component="pipeline"
        )
        self.content = content[:100]  # Truncate for logging
        self.detected_pattern = detected_pattern
