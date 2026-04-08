"""tools.py — Custom CrewAI tools for NVIDIA API-powered extraction.

Each tool wraps an NVIDIA endpoint behind a robust try/except boundary so
that failures are captured as error strings rather than uncaught exceptions—
keeping the upstream Super Agent stable.

All model IDs, prompts, timeouts, and tunable parameters are read from
``config.py`` — never hardcoded here.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import tempfile
import traceback
from pathlib import Path
from typing import Type

import cv2
import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import (
    API,
    MODELS,
    VISION_CFG,
    AUDIO_CFG,
    VIDEO_CFG,
    EXTENSION_MAP,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    """Return the NVIDIA API key from config or raise."""
    if not API.api_key:
        raise EnvironmentError(
            "NVIDIA_API_KEY is not set. "
            "Export it or add it to your .env file."
        )
    return API.api_key


def detect_mime_type(file_path: str) -> str:
    """Detect MIME type of a file using the mimetypes stdlib module.

    Args:
        file_path: Absolute or relative path to the target file.

    Returns:
        A MIME type string, e.g. ``image/png``.  Falls back to
        ``application/octet-stream`` when detection fails.
    """
    mime, _ = mimetypes.guess_type(file_path)
    return mime or "application/octet-stream"


def detect_media_type(file_path: str) -> str:
    """Map a file extension to one of the canonical media type strings.

    Args:
        file_path: Path to the file.

    Returns:
        One of ``image``, ``document``, ``audio``, ``video``, or ``unknown``.
    """
    ext = Path(file_path).suffix.lower()
    return EXTENSION_MAP.get(ext, "unknown")


def _encode_file_to_base64(file_path: str) -> str:
    """Read a file and return its base64-encoded contents.

    Args:
        file_path: Absolute path to the file.

    Returns:
        Base64 string.
    """
    with open(file_path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("utf-8")


def _encode_image_to_data_uri(file_path: str) -> str:
    """Encode an image file as a data URI suitable for vision API payloads.

    Args:
        file_path: Absolute path to the image/document file.

    Returns:
        A ``data:<mime>;base64,<data>`` string.
    """
    mime = detect_mime_type(file_path)
    b64 = _encode_file_to_base64(file_path)
    return f"data:{mime};base64,{b64}"


# =========================================================================
# Tool 1 — Image & Document OCR (Vision Model)
# =========================================================================

class VisionOCRToolInput(BaseModel):
    """Input schema for the VisionOCRTool."""
    file_path: str = Field(..., description="Absolute path to an image or PDF file.")


class VisionOCRTool(BaseTool):
    """Extract text, tables, and OCR data from images and PDF documents
    using the configured vision model on NVIDIA's API.
    """

    name: str = "vision_ocr_tool"
    description: str = (
        "Extracts all visible text, tables, and OCR data from image files "
        "(PNG, JPG, TIFF, BMP, WEBP, GIF) and PDF documents by sending them "
        "to the NVIDIA Vision model. Returns the extracted text "
        "as a string. Input: absolute file path."
    )
    args_schema: Type[BaseModel] = VisionOCRToolInput

    def _run(self, file_path: str) -> str:
        """Execute vision-based OCR extraction.

        Args:
            file_path: Absolute path to the image or document.

        Returns:
            Extracted text on success, or a prefixed error string on failure.
        """
        try:
            api_key = _get_api_key()
            data_uri = _encode_image_to_data_uri(file_path)

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            payload = {
                "model": MODELS.vision,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": VISION_CFG.prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": data_uri},
                            },
                        ],
                    }
                ],
                "max_tokens": VISION_CFG.max_tokens,
                "temperature": VISION_CFG.temperature,
                "stream": False,
            }

            response = requests.post(
                f"{API.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=VISION_CFG.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        except Exception as exc:
            return f"[TOOL_ERROR] VisionOCRTool failed: {exc}\n{traceback.format_exc()}"


# =========================================================================
# Tool 2 — Audio Transcription (ASR)
# =========================================================================

class AudioTranscriptionToolInput(BaseModel):
    """Input schema for the AudioTranscriptionTool."""
    file_path: str = Field(..., description="Absolute path to an audio file (.mp3, .wav, etc.).")


class AudioTranscriptionTool(BaseTool):
    """Transcribe audio files to text using the configured NVIDIA ASR model."""

    name: str = "audio_transcription_tool"
    description: str = (
        "Transcribes speech from audio files (MP3, WAV, FLAC, OGG, M4A, AAC) "
        "into text using NVIDIA's hosted ASR model. Returns the full "
        "transcript as a string. Input: absolute file path."
    )
    args_schema: Type[BaseModel] = AudioTranscriptionToolInput

    def _run(self, file_path: str) -> str:
        """Execute audio transcription.

        Args:
            file_path: Absolute path to the audio file.

        Returns:
            Transcript text on success, or a prefixed error string on failure.
        """
        try:
            api_key = _get_api_key()

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            }

            mime = detect_mime_type(file_path)
            with open(file_path, "rb") as audio_file:
                files = {
                    "file": (Path(file_path).name, audio_file, mime),
                }
                data = {
                    "model": MODELS.audio_asr,
                    "language": AUDIO_CFG.language,
                }

                response = requests.post(
                    f"{API.base_url}/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=AUDIO_CFG.timeout_seconds,
                )

            response.raise_for_status()
            result = response.json()
            return result.get("text", str(result))

        except Exception as exc:
            return f"[TOOL_ERROR] AudioTranscriptionTool failed: {exc}\n{traceback.format_exc()}"


# =========================================================================
# Tool 3 — Video Extraction (Frame Sampling + Vision)
# =========================================================================

class VideoExtractionToolInput(BaseModel):
    """Input schema for the VideoExtractionTool."""
    file_path: str = Field(..., description="Absolute path to a video file (.mp4, .mov, etc.).")


class VideoExtractionTool(BaseTool):
    """Extract on-screen text and summarise visual events from video files.

    Strategy: sample key frames with OpenCV, send each frame to the NVIDIA
    vision model, and aggregate the results.
    """

    name: str = "video_extraction_tool"
    description: str = (
        "Extracts on-screen text and summarises visual events from video "
        "files (MP4, MOV, AVI, MKV, WEBM). Uses OpenCV to sample key frames "
        "and the NVIDIA Vision model to OCR each frame. Returns aggregated "
        "text. Input: absolute file path."
    )
    args_schema: Type[BaseModel] = VideoExtractionToolInput

    def _sample_frames(self, file_path: str) -> list[str]:
        """Sample frames from a video at fixed intervals.

        Args:
            file_path: Path to the video file.

        Returns:
            List of temporary file paths for extracted JPEG frames.
        """
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {file_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps

        interval = max(
            VIDEO_CFG.frame_interval_seconds,
            duration / VIDEO_CFG.max_frames,
        )
        sample_times: list[float] = []
        t = 0.0
        while t < duration and len(sample_times) < VIDEO_CFG.max_frames:
            sample_times.append(t)
            t += interval

        frame_paths: list[str] = []
        tmp_dir = tempfile.mkdtemp(prefix="omni_ocr_frames_")

        for idx, ts in enumerate(sample_times):
            cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
            ret, frame = cap.read()
            if not ret:
                continue
            frame_file = os.path.join(tmp_dir, f"frame_{idx:04d}.jpg")
            cv2.imwrite(frame_file, frame)
            frame_paths.append(frame_file)

        cap.release()
        return frame_paths

    def _ocr_frame(self, frame_path: str, frame_index: int) -> str:
        """Run OCR on a single frame via the NVIDIA vision model.

        Args:
            frame_path: Path to the JPEG frame.
            frame_index: Zero-based index for labelling.

        Returns:
            Extracted text prefixed with a frame marker.
        """
        api_key = _get_api_key()
        data_uri = _encode_image_to_data_uri(frame_path)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "model": MODELS.vision,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": VIDEO_CFG.frame_prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        },
                    ],
                }
            ],
            "max_tokens": VIDEO_CFG.per_frame_max_tokens,
            "temperature": VIDEO_CFG.per_frame_temperature,
            "stream": False,
        }

        response = requests.post(
            f"{API.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=VIDEO_CFG.per_frame_timeout,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return f"[Frame {frame_index}]\n{text}"

    def _run(self, file_path: str) -> str:
        """Execute video extraction pipeline.

        Args:
            file_path: Absolute path to the video file.

        Returns:
            Aggregated OCR / description text from sampled frames,
            or a prefixed error string on failure.
        """
        try:
            frame_paths = self._sample_frames(file_path)
            if not frame_paths:
                return "[TOOL_ERROR] VideoExtractionTool: No frames could be sampled."

            results: list[str] = []
            for idx, fp in enumerate(frame_paths):
                try:
                    result = self._ocr_frame(fp, idx)
                    results.append(result)
                except Exception as frame_exc:
                    results.append(
                        f"[Frame {idx}] [FRAME_ERROR] {frame_exc}"
                    )
                finally:
                    try:
                        os.remove(fp)
                    except OSError:
                        pass

            return "\n\n".join(results)

        except Exception as exc:
            return f"[TOOL_ERROR] VideoExtractionTool failed: {exc}\n{traceback.format_exc()}"
