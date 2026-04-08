"""
Content extractor for Omni Browser Agent.
Extracts content from YouTube, Instagram, LinkedIn, and Twitter/X.
"""

import re
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from core.logger import get_component_logger
from core.config import get_settings
from core.exceptions import (
    TranscriptUnavailableError,
    MediaDownloadError,
    AudioProcessingError,
)
from models.schemas import (
    Platform,
    YouTubeVideo,
    InstagramPost,
    LinkedInPost,
    Tweet,
    ExtractionResult,
)
from auth.manager import get_auth_manager


class BaseExtractor:
    """Base extractor for platform content."""

    def __init__(self, platform: Platform):
        self.logger = get_component_logger(f"extractor.{platform.value}")
        self.platform = platform
        self.settings = get_settings()
        self.auth_manager = get_auth_manager()

    async def extract(self, url: str) -> ExtractionResult:
        """Extract content from URL."""
        raise NotImplementedError

    def _extract_video_id(self, url: str, platform: str) -> Optional[str]:
        """Extract video/post ID from URL."""
        parsed = urlparse(url)

        if platform == "youtube":
            # Handle various YouTube URL formats
            if "youtube.com" in parsed.netloc:
                query = parse_qs(parsed.query)
                if "v" in query:
                    return query["v"][0]
                # Handle /watch path
                if "/watch" in parsed.path:
                    return parse_qs(parsed.query).get("v", [None])[0]
                # Handle short URLs
                if "/shorts/" in parsed.path:
                    return parsed.path.split("/shorts/")[1].split("?")[0]
            elif "youtu.be" in parsed.netloc:
                return parsed.path.lstrip("/")

        elif platform == "instagram":
            # Extract post ID from Instagram URL
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                return parts[-1] if parts[-1] != "" else parts[-2]

        elif platform == "linkedin":
            # Extract post ID from LinkedIn URL
            if "/feed/" in parsed.path or "/posts/" in parsed.path:
                parts = parsed.path.strip("/").split("/")
                return parts[-1] if parts else None

        elif platform == "twitter":
            # Extract tweet ID from URL
            if "/status/" in parsed.path:
                return parsed.path.split("/status/")[-1].split("?")[0]

        return None


class YouTubeExtractor(BaseExtractor):
    """YouTube content extractor with 3-path transcript waterfall."""

    def __init__(self):
        super().__init__(Platform.YOUTUBE)

    async def extract(self, url: str) -> ExtractionResult:
        """Extract content from YouTube video."""
        video_id = self._extract_video_id(url, "youtube")

        if not video_id:
            return ExtractionResult(
                success=False, platform=Platform.YOUTUBE, error="Invalid YouTube URL"
            )

        self.logger.info(f"Extracting YouTube video: {video_id}")

        # Try transcript API first
        transcript = None
        if self.settings.social.youtube_transcript_api_enabled:
            transcript = await self._try_transcript_api(video_id)

        # Try yt-dlp if no transcript
        if not transcript:
            try:
                transcript = await self._try_yt_dlp(video_id, url)
            except Exception as e:
                self.logger.warning(f"yt-dlp extraction failed: {e}")

        # Build result
        video_data = await self._get_video_metadata(video_id, url)

        if transcript:
            video_data["transcript"] = transcript

        # Create YouTubeVideo object
        youtube_video = YouTubeVideo(
            post_id=video_id,
            url=url,
            timestamp=video_data.get("timestamp", datetime.utcnow()),
            author=video_data.get("author", ""),
            content=video_data.get("description", ""),
            title=video_data.get("title", ""),
            duration=video_data.get("duration", 0),
            view_count=video_data.get("view_count", 0),
            transcript=transcript,
            media_urls=video_data.get("media_urls", []),
        )

        return ExtractionResult(
            success=True,
            platform=Platform.YOUTUBE,
            posts=[youtube_video],
            extracted_text=transcript or video_data.get("description", ""),
        )

    async def _try_transcript_api(self, video_id: str) -> Optional[str]:
        """Try using youtube-transcript-api."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([item["text"] for item in transcript])
            self.logger.info("Transcript extracted via youtube-transcript-api")
            return text
        except Exception as e:
            self.logger.warning(f"youtube-transcript-api failed: {e}")
            return None

    async def _try_yt_dlp(self, video_id: str, url: str) -> Optional[str]:
        """Try using yt-dlp for audio extraction + Whisper."""
        try:
            import yt_dlp

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"downloads/{video_id}.%(ext)s",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "wav",
                    }
                ],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            # Now process audio with Whisper
            audio_path = f"downloads/{video_id}.wav"

            # This would use Whisper for transcription
            # For now, return placeholder
            self.logger.info(f"Downloaded audio to {audio_path}")

            # VAD check would go here
            # If music only, return "Audio: Music/Non-vocal"

            return None

        except Exception as e:
            self.logger.warning(f"yt-dlp extraction failed: {e}")
            return None

    async def _get_video_metadata(self, video_id: str, url: str) -> Dict[str, Any]:
        """Get video metadata via oEmbed or API."""
        # Placeholder - in real implementation would use YouTube Data API
        return {
            "title": f"YouTube Video {video_id}",
            "description": "Video description",
            "author": "Unknown",
            "duration": 0,
            "view_count": 0,
            "timestamp": datetime.utcnow(),
        }


class InstagramExtractor(BaseExtractor):
    """Instagram content extractor mirroring Anti-Gravity Media Engine workflow."""

    def __init__(self):
        super().__init__(Platform.INSTAGRAM)

    async def extract(self, url: str) -> ExtractionResult:
        """Extract content from Instagram post by downloading, extracting frames, and analyzing."""
        post_id = self._extract_video_id(url, "instagram")

        if not post_id:
            return ExtractionResult(
                success=False,
                platform=Platform.INSTAGRAM,
                error="Invalid Instagram URL",
            )

        self.logger.info(f"Extracting Instagram post: {post_id}")

        import os
        import tempfile
        import shutil

        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp(prefix=f"ig_extract_{post_id}_")
        video_path = os.path.join(temp_dir, f"{post_id}.mp4")

        try:
            # 1. Download Video
            downloaded_path = await self._download_video(url, video_path)
            if not downloaded_path:
                return ExtractionResult(
                    success=False,
                    platform=Platform.INSTAGRAM,
                    error="Failed to download Instagram video",
                )

            # 2. Extract Text-Heavy Frames (OCR)
            frames_b64 = await self._extract_frames(downloaded_path)
            
            # 3. Vision AI Inference
            ai_inference = None
            try:
                from pipeline.ai_inference import get_ai_inference
                ai_inference = get_ai_inference()
            except ImportError:
                self.logger.warning("AI Inference module not found.")
            
            prompt_text = ""
            if ai_inference and frames_b64:
                prompt_text = await self._analyze_video_content(frames_b64, ai_inference)
            elif not frames_b64:
                prompt_text = "[No text-heavy frames detected in video]"

            # 4. Privacy Guard (Scrub PII)
            try:
                from pipeline.privacy_guard import get_privacy_guard
                privacy_guard = get_privacy_guard()
                prompt_text = privacy_guard.scrub_pii(prompt_text)
            except Exception as e:
                self.logger.warning(f"Failed to scrub PII: {e}")

            # Prepare Result
            instagram_post = InstagramPost(
                post_id=post_id,
                url=url,
                timestamp=datetime.utcnow(),
                author="instagram_creator", # Real metadata needs auth, keeping it generic for now
                caption="Prompt Extraction from Video",
                media_type="video",
                content=prompt_text,
            )

            return ExtractionResult(
                success=True,
                platform=Platform.INSTAGRAM,
                posts=[instagram_post],
                extracted_text=prompt_text,
            )

        except Exception as e:
            self.logger.error(f"Error extracting Instagram content: {e}")
            return ExtractionResult(
                success=False,
                platform=Platform.INSTAGRAM,
                error=f"Error extracting Instagram content: {str(e)}",
            )
        finally:
            # Clean up temp files
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
                
    async def _download_video(self, url: str, output_path: str) -> str:
        """Download video via yt-dlp with 'Unstoppable' fallback logic."""
        import yt_dlp
        
        cookies_arg = None
        # Try to find Netscape cookies if they exist in the workspace
        if os.path.exists("ig_cookies_netscape.txt"):
            cookies_arg = "ig_cookies_netscape.txt"
            
        def try_download(ydl_options):
            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                ydl.extract_info(url, download=True)
                
        # Phase 1: Try best quality with cookies
        opts_best = {
            "format": "best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
        }
        if cookies_arg:
            opts_best["cookiefile"] = cookies_arg
            
        try:
            self.logger.info(f"Downloading video from {url} (Phase 1)")
            try_download(opts_best)
            return output_path
        except Exception as e:
            self.logger.warning(f"Phase 1 download failed: {e}")
            
        # Phase 2: Try without cookies and ignore some errors
        opts_fallback = {
            "format": "best",
            "outtmpl": output_path,
            "ignoreerrors": True,
            "quiet": True,
            "no_warnings": True,
        }
        try:
            self.logger.info(f"Downloading video from {url} (Phase 2 - Fallback)")
            try_download(opts_fallback)
            if os.path.exists(output_path):
                return output_path
        except Exception as e:
            self.logger.error(f"Fallback download failed: {e}")
            
        return ""

    async def _extract_frames(self, video_path: str) -> List[str]:
        """Extract frames using cv2 and keep text-heavy frames via EasyOCR."""
        self.logger.info("Extracting frames via OpenCV and filtering via EasyOCR...")
        try:
            import cv2
            import easyocr
            import base64
        except ImportError:
            self.logger.error("Missing cv2 or easyocr. Cannot extract frames.")
            return []

        # Initialize EasyOCR reader (only load English into memory)
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        
        frames_b64 = []
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0 # fallback
                
            frame_interval = int(fps * 2) # every 2 seconds
            
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_idx % frame_interval == 0:
                    # Run EasyOCR
                    result = reader.readtext(frame)
                    words_detected = [res[1] for res in result]
                    
                    if len(words_detected) >= 8:
                        self.logger.info(f"Found dense text frame at index {frame_idx} with {len(words_detected)} words.")
                        # Convert to base64 jpeg
                        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                        b64_str = base64.b64encode(buffer).decode('utf-8')
                        frames_b64.append(b64_str)
                        
                frame_idx += 1
                
            cap.release()
            return frames_b64
        except Exception as e:
            self.logger.error(f"Error during frame extraction: {e}")
            return []

    async def _analyze_video_content(self, frames_b64: List[str], ai_inference) -> str:
        """Send extracted frames to Vision AI one at a time and compile result."""
        self.logger.info(f"Sending {len(frames_b64)} frames to Vision AI...")
        
        extracted_texts = []
        for i, b64 in enumerate(frames_b64):
            prompt = "Extract any prompt, text or configuration parameters visible in this image. Only return the exact text you see."
            import base64
            image_bytes = base64.b64decode(b64)
            
            try:
                res = await ai_inference.vision(image_bytes=image_bytes, prompt=prompt)
                if res.success and res.text:
                    extracted_texts.append(f"--- Frame {i} ---\n{res.text}")
            except Exception as e:
                self.logger.warning(f"Vision inference failed for frame {i}: {e}")
                
        if not extracted_texts:
            return "[No text could be interpreted from the frames]"
            
        merged_text = "\n".join(extracted_texts)
        
        # Phase 2: Merge prompt
        merge_prompt = f"Combine the following pieces of extracted text into one cohesive AI generation prompt. Remove duplicates and noise. Text:\n{merged_text}"
        
        try:
            from pipeline.ai_inference import run_llm_completion
            final_prompt = await run_llm_completion([{"role": "user", "content": merge_prompt}])
            return final_prompt
        except Exception as e:
            self.logger.warning(f"LLM merge failed, returning concatenated text: {e}")
            return merged_text


class LinkedInExtractor(BaseExtractor):
    """LinkedIn content extractor."""

    def __init__(self):
        super().__init__(Platform.LINKEDIN)

    async def extract(self, url: str) -> ExtractionResult:
        """Extract content from LinkedIn post."""
        post_id = self._extract_video_id(url, "linkedin")

        if not post_id:
            return ExtractionResult(
                success=False, platform=Platform.LINKEDIN, error="Invalid LinkedIn URL"
            )

        self.logger.info(f"Extracting LinkedIn post: {post_id}")

        # Check auth
        try:
            session = await self.auth_manager.get_linkedin_session()
        except Exception as e:
            self.logger.warning(f"LinkedIn auth issue: {e}")

        # Placeholder extraction
        if self.settings.enable_demo_mode:
            linkedin_post = LinkedInPost(
                post_id=post_id,
                url=url,
                timestamp=datetime.utcnow(),
                author="demo_user",
                content="Demo LinkedIn post",
                post_type="update",
            )

            return ExtractionResult(
                success=True, platform=Platform.LINKEDIN, posts=[linkedin_post]
            )

        return ExtractionResult(
            success=False,
            platform=Platform.LINKEDIN,
            error="LinkedIn extraction requires authentication",
        )


class TwitterExtractor(BaseExtractor):
    """Twitter/X content extractor."""

    def __init__(self):
        super().__init__(Platform.TWITTER)

    async def extract(self, url: str) -> ExtractionResult:
        """Extract content from Twitter post."""
        tweet_id = self._extract_video_id(url, "twitter")

        if not tweet_id:
            return ExtractionResult(
                success=False, platform=Platform.TWITTER, error="Invalid Twitter URL"
            )

        self.logger.info(f"Extracting Twitter post: {tweet_id}")

        # Check auth
        bearer_token = self.auth_manager.get_twitter_bearer_token()

        # Placeholder extraction - would use Twitter API v2
        if self.settings.enable_demo_mode:
            tweet = Tweet(
                post_id=tweet_id,
                url=url,
                timestamp=datetime.utcnow(),
                author="demo_user",
                content="Demo tweet content",
            )

            return ExtractionResult(
                success=True, platform=Platform.TWITTER, posts=[tweet]
            )

        return ExtractionResult(
            success=False,
            platform=Platform.TWITTER,
            error="Twitter extraction requires API authentication",
        )


# Factory function
def get_extractor(platform: Platform) -> BaseExtractor:
    """Get extractor for specified platform."""
    extractors = {
        Platform.YOUTUBE: YouTubeExtractor,
        Platform.INSTAGRAM: InstagramExtractor,
        Platform.LINKEDIN: LinkedInExtractor,
        Platform.TWITTER: TwitterExtractor,
    }

    extractor_class = extractors.get(platform)
    if not extractor_class:
        raise ValueError(f"No extractor for platform: {platform}")

    return extractor_class()
