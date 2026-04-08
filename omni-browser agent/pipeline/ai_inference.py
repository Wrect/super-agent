"""
AI inference wrappers for Omni Browser Agent.
Provides async wrappers for NVIDIA vision, ASR, and LLM inference.
"""

import base64
import io
from typing import Dict, Any, Optional, List

from core.logger import get_component_logger
from core.config import get_settings


class VisionResult:
    """Result of vision model inference."""

    def __init__(
        self,
        success: bool,
        text: str = "",
        bounding_boxes: Optional[List[Dict]] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.text = text
        self.bounding_boxes = bounding_boxes or []
        self.error = error

    def __str__(self) -> str:
        return self.text if self.success else f"Error: {self.error}"


class TranscriptionResult:
    """Result of audio transcription."""

    def __init__(
        self,
        success: bool,
        text: str = "",
        language: Optional[str] = None,
        confidence: float = 0.0,
        error: Optional[str] = None,
    ):
        self.success = success
        self.text = text
        self.language = language
        self.confidence = confidence
        self.error = error

    def __str__(self) -> str:
        return self.text if self.success else f"Error: {self.error}"


async def run_vision_analysis(
    image_bytes: bytes,
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
) -> str:
    """
    Run NVIDIA vision model inference on an image.

    Args:
        image_bytes: Image data as bytes
        prompt: Text prompt for the vision model
        model: Optional model override
        temperature: Sampling temperature

    Returns:
        Vision model response text
    """
    logger = get_component_logger("ai_inference")
    settings = get_settings()

    model = model or settings.ai.vision_model

    logger.debug(f"Running vision analysis with model: {model}")

    # Demo mode - return stub response
    if settings.enable_demo_mode:
        logger.warning("Using demo mode for vision analysis")
        return """
        {
            "action": "extract",
            "reasoning": "Demo mode - extracting page content",
            "selector": null,
            "value": null
        }
        """

    # Real implementation using httpx
    try:
        import httpx
        
        # Flexibility: If model is a full URL, use it as the endpoint
        api_endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
        if model and model.startswith("http"):
            api_endpoint = model
            # Extract just the name if it's a URL (often everything after the last slash)
            model_name = model.split("/")[-1]
        else:
            model_name = model
            
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        headers = {
            "Authorization": f"Bearer {settings.nvidia_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                }
            ],
            "max_tokens": 512,
            "temperature": temperature,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                api_endpoint,
                headers=headers,
                json=payload
            )
            if response.status_code == 404:
                # Often NVIDIA URLs need specific suffixes for specific models
                logger.error(f"404 Error at {api_endpoint}. Model '{model_name}' might not be on this endpoint.")
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
    except Exception as e:
        logger.error(f"NVIDIA vision inference failed ({model}): {str(e)}")
        # Default fallback extraction structure so it doesn't hard-crash the router
        return f'{{\n  "action": "extract",\n  "reasoning": "Error calling API ({model}): {str(e)}",\n  "selector": null,\n  "value": null\n}}'


async def run_audio_transcription(
    audio_path: str, language: Optional[str] = None, model: Optional[str] = None
) -> TranscriptionResult:
    """
    Run audio transcription using Whisper or NVIDIA ASR.

    Args:
        audio_path: Path to audio file
        language: Optional language code
        model: Optional model override

    Returns:
        TranscriptionResult object
    """
    logger = get_component_logger("ai_inference")
    settings = get_settings()

    model = model or settings.ai.audio_model

    logger.debug(f"Running audio transcription with model: {model}")

    # Demo mode
    if settings.enable_demo_mode:
        logger.warning("Using demo mode for audio transcription")
        return TranscriptionResult(
            success=True,
            text="Demo transcription of audio content",
            language=language or "en",
            confidence=0.9,
        )

    # Real implementation would use:
    # 1. whisper or faster-whisper for local inference
    # 2. NVIDIA NIM ASR API for cloud inference

    logger.warning("NVIDIA ASR inference not fully implemented")

    return TranscriptionResult(
        success=False, error="Audio transcription not configured"
    )


async def run_llm_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Run LLM completion using NVIDIA NIM or fallback.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Optional model override
        temperature: Sampling temperature
        max_tokens: Optional max tokens

    Returns:
        LLM response text
    """
    logger = get_component_logger("ai_inference")
    settings = get_settings()

    model = model or settings.ai.llm_model

    logger.debug(f"Running LLM completion with model: {model}")

    # Demo mode
    if settings.enable_demo_mode:
        logger.warning("Using demo mode for LLM completion")
        return "Demo LLM response to: " + messages[-1].get("content", "")[:50]

    try:
        import httpx
        headers = {
            "Authorization": f"Bearer {settings.nvidia_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
    except Exception as e:
        logger.error(f"NVIDIA LLM inference failed: {str(e)}")
        raise e


async def run_vad(audio_path: str) -> Dict[str, Any]:
    """
    Run Voice Activity Detection on audio.

    Args:
        audio_path: Path to audio file

    Returns:
        Dict with VAD results (has_speech, voice_type, etc.)
    """
    logger = get_component_logger("ai_inference")
    settings = get_settings()

    # Demo mode
    if settings.enable_demo_mode:
        return {"has_speech": True, "voice_type": "speech", "confidence": 0.85}

    # Real implementation would use:
    # - WebRTC VAD
    # - Silero VAD
    # - Or NVIDIA audio processing

    return {"has_speech": True, "voice_type": "speech", "confidence": 0.5}


class AIInference:
    """
    AI inference manager for unified access to all AI models.
    """

    def __init__(self):
        self.logger = get_component_logger("ai_inference")
        self.settings = get_settings()

    async def vision(self, image_bytes: bytes, prompt: str, **kwargs) -> VisionResult:
        """Run vision analysis."""
        result_text = await run_vision_analysis(image_bytes, prompt, **kwargs)
        return VisionResult(success=True, text=result_text)

    async def transcription(
        self, audio_path: str, language: Optional[str] = None, **kwargs
    ) -> TranscriptionResult:
        """Run audio transcription."""
        return await run_audio_transcription(audio_path, language, **kwargs)

    async def llm(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Run LLM completion."""
        return await run_llm_completion(messages, **kwargs)

    async def vad(self, audio_path: str) -> Dict[str, Any]:
        """Run voice activity detection."""
        return await run_vad(audio_path)


# Global AI inference instance
_ai_inference: Optional[AIInference] = None


def get_ai_inference() -> AIInference:
    """Get singleton AI inference instance."""
    global _ai_inference
    if _ai_inference is None:
        _ai_inference = AIInference()
    return _ai_inference
