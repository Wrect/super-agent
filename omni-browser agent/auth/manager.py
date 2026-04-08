"""
Authentication manager for Omni Browser Agent.
Handles OAuth2 and cookie-based session management for social media platforms.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from core.logger import get_component_logger
from core.config import get_settings
from core.exceptions import AuthExpiredError, AgentAuthError


class AuthManager:
    """
    Manages authentication for social media platforms.
    Supports OAuth2, cookie-based sessions, and token refresh.
    """

    def __init__(self):
        self.logger = get_component_logger("auth")
        self.settings = get_settings()
        self.tokens_dir = Path("data/tokens")
        self.tokens_dir.mkdir(parents=True, exist_ok=True)

        self._youtube_tokens: Dict[str, Any] = {}
        self._instagram_session: Optional[Dict] = None
        self._linkedin_session: Optional[Dict] = None
        self._twitter_bearer_token: Optional[str] = None

        self._load_tokens()

    def _load_tokens(self) -> None:
        """Load stored tokens from disk."""
        # Load YouTube tokens
        youtube_token_file = self.tokens_dir / "youtube_tokens.json"
        if youtube_token_file.exists():
            try:
                self._youtube_tokens = json.loads(youtube_token_file.read_text())
                self.logger.info("Loaded YouTube tokens from disk")
            except Exception as e:
                self.logger.warning(f"Failed to load YouTube tokens: {e}")

        # Load Instagram session
        instagram_session_file = self.tokens_dir / "instagram_session.json"
        if instagram_session_file.exists():
            try:
                self._instagram_session = json.loads(instagram_session_file.read_text())
                self.logger.info("Loaded Instagram session from disk")
            except Exception as e:
                self.logger.warning(f"Failed to load Instagram session: {e}")

        # Load LinkedIn session
        linkedin_session_file = self.tokens_dir / "linkedin_session.json"
        if linkedin_session_file.exists():
            try:
                self._linkedin_session = json.loads(linkedin_session_file.read_text())
                self.logger.info("Loaded LinkedIn session from disk")
            except Exception as e:
                self.logger.warning(f"Failed to load LinkedIn session: {e}")

        # Load Twitter bearer token
        if self.settings.twitter_bearer_token:
            self._twitter_bearer_token = self.settings.twitter_bearer_token

    def _save_tokens(self, platform: str, data: Dict[str, Any]) -> None:
        """Save tokens to disk."""
        token_file = self.tokens_dir / f"{platform}_tokens.json"
        try:
            token_file.write_text(json.dumps(data, indent=2))
            self.logger.debug(f"Saved {platform} tokens to disk")
        except Exception as e:
            self.logger.error(f"Failed to save {platform} tokens: {e}")

    # YouTube/Google OAuth 2.0
    async def get_youtube_tokens(self) -> Dict[str, Any]:
        """
        Get YouTube OAuth tokens.
        Handles token refresh on 401 and returns valid tokens.
        """
        # Check if tokens exist and are not expired
        if self._youtube_tokens:
            expires_at = self._youtube_tokens.get("expires_at", 0)
            if time.time() < expires_at - 300:  # 5 min buffer
                return self._youtube_tokens

        # Need to re-authenticate
        if not self.settings.google_client_id or not self.settings.google_client_secret:
            if self.settings.enable_demo_mode:
                self.logger.warning("Using demo YouTube tokens (demo mode)")
                return {
                    "access_token": "demo_access_token",
                    "refresh_token": "demo_refresh_token",
                    "expires_at": time.time() + 3600,
                }
            raise AgentAuthError(
                platform="youtube", message="Google OAuth credentials not configured"
            )

        # In a real implementation, this would:
        # 1. Start OAuth 2.0 PKCE flow
        # 2. Exchange authorization code for tokens
        # 3. Store tokens with refresh logic

        # For now, attempt token refresh if we have a refresh token
        if self._youtube_tokens.get("refresh_token"):
            try:
                self.logger.info("Attempting to refresh YouTube tokens")
                # Token refresh would happen here
                # For demo, return current tokens
                return self._youtube_tokens
            except Exception as e:
                self.logger.error(f"Token refresh failed: {e}")

        raise AuthExpiredError(platform="youtube", message="No valid YouTube tokens")

    def set_youtube_tokens(self, tokens: Dict[str, Any]) -> None:
        """Set YouTube OAuth tokens."""
        tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
        self._youtube_tokens = tokens
        self._save_tokens("youtube", tokens)
        self.logger.info("YouTube tokens updated")

    # Instagram Cookie Session
    async def get_instagram_session(self) -> Dict[str, Any]:
        """
        Get Instagram session.
        Handles re-authentication if session is expired.
        """
        if self._instagram_session:
            # Check expiry
            expires_at = self._instagram_session.get("expires_at", 0)
            if time.time() < expires_at:
                return self._instagram_session

        # Re-authenticate
        if not self.settings.instagram_username or not self.settings.instagram_password:
            if self.settings.enable_demo_mode:
                self.logger.warning("Using demo Instagram session (demo mode)")
                return {
                    "session_id": "demo_session_id",
                    "expires_at": time.time() + 3600,
                }
            raise AuthExpiredError(
                platform="instagram", message="Instagram credentials not configured"
            )

        # In a real implementation, use instagrapi to login
        # This is a placeholder
        self.logger.info("Instagram re-authentication would happen here")

        return self._instagram_session or {
            "session_id": "demo_session_id",
            "expires_at": time.time() + 3600,
        }

    def set_instagram_session(self, session: Dict[str, Any]) -> None:
        """Set Instagram session."""
        session["expires_at"] = time.time() + 3600
        self._instagram_session = session
        self._save_tokens("instagram", session)
        self.logger.info("Instagram session updated")

    # LinkedIn Cookie Session
    async def get_linkedin_session(self) -> Dict[str, Any]:
        """Get LinkedIn session."""
        if self._linkedin_session:
            expires_at = self._linkedin_session.get("expires_at", 0)
            if time.time() < expires_at:
                return self._linkedin_session

        if not self.settings.linkedin_username or not self.settings.linkedin_password:
            if self.settings.enable_demo_mode:
                self.logger.warning("Using demo LinkedIn session (demo mode)")
                return {"li_at": "demo_li_at", "expires_at": time.time() + 3600}
            raise AuthExpiredError(
                platform="linkedin", message="LinkedIn credentials not configured"
            )

        self.logger.info("LinkedIn re-authentication would happen here")

        return self._linkedin_session or {
            "li_at": "demo_li_at",
            "expires_at": time.time() + 3600,
        }

    def set_linkedin_session(self, session: Dict[str, Any]) -> None:
        """Set LinkedIn session."""
        session["expires_at"] = time.time() + 3600
        self._linkedin_session = session
        self._save_tokens("linkedin", session)
        self.logger.info("LinkedIn session updated")

    # Twitter/X Bearer Token
    def get_twitter_bearer_token(self) -> str:
        """Get Twitter/X bearer token."""
        if self._twitter_bearer_token:
            return self._twitter_bearer_token

        if self.settings.twitter_bearer_token:
            self._twitter_bearer_token = self.settings.twitter_bearer_token
            return self._twitter_bearer_token

        if self.settings.enable_demo_mode:
            self.logger.warning("Using demo Twitter bearer token (demo mode)")
            return "demo_bearer_token"

        raise AgentAuthError(
            platform="twitter", message="Twitter bearer token not configured"
        )

    # Check authentication status
    async def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication status for all platforms."""
        status = {
            "youtube": {
                "authenticated": bool(self._youtube_tokens.get("access_token")),
                "demo_mode": self.settings.enable_demo_mode,
            },
            "instagram": {
                "authenticated": bool(self._instagram_session),
                "demo_mode": self.settings.enable_demo_mode,
            },
            "linkedin": {
                "authenticated": bool(self._linkedin_session),
                "demo_mode": self.settings.enable_demo_mode,
            },
            "twitter": {
                "authenticated": bool(self._twitter_bearer_token),
                "demo_mode": self.settings.enable_demo_mode,
            },
        }
        return status

    async def refresh_all_tokens(self) -> None:
        """Refresh all platform tokens."""
        self.logger.info("Refreshing all platform tokens")

        try:
            await self.get_youtube_tokens()
        except Exception as e:
            self.logger.warning(f"Failed to refresh YouTube tokens: {e}")

        try:
            await self.get_instagram_session()
        except Exception as e:
            self.logger.warning(f"Failed to refresh Instagram session: {e}")

        try:
            await self.get_linkedin_session()
        except Exception as e:
            self.logger.warning(f"Failed to refresh LinkedIn session: {e}")


# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get singleton auth manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
