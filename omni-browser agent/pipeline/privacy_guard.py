"""
Privacy Guard for Omni Browser Agent.
Scans extracted text for PII and replaces them with redacted tags using Presidio.
"""

from typing import Dict, Any, Union, List
from core.logger import get_component_logger

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False


class PrivacyGuard:
    """
    Scans and redacts PII (Personally Identifiable Information).
    Catches phone numbers, emails, persons, and locations.
    """
    
    def __init__(self):
        self.logger = get_component_logger("privacy_guard")
        self.analyzer = None
        self.anonymizer = None
        
        if PRESIDIO_AVAILABLE:
            try:
                # Note: this might take a bit to load the first time or require "python -m spacy download en_core_web_lg"
                self.analyzer = AnalyzerEngine()
                self.anonymizer = AnonymizerEngine()
                self.logger.info("Presidio Privacy Guard initialized successfully.")
            except Exception as e:
                self.logger.error(f"Failed to initialize Presidio: {e}")
        else:
            self.logger.warning("Presidio packages not installed. PII scrubbing is disabled.")

    def scrub_text(self, text: str) -> str:
        """
        Runs Presidio analyzer + anonymizer on a single string.
        """
        if not text or not self.analyzer or not self.anonymizer:
            return text
            
        try:
            # Detect PII entities
            results = self.analyzer.analyze(
                text=text,
                entities=["PHONE_NUMBER", "EMAIL_ADDRESS", "PERSON", "LOCATION"],
                language='en'
            )
            
            # Anonymize (redact) the entities
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results
            )
            return anonymized_result.text
        except Exception as e:
            self.logger.error(f"Error scrubbing text: {e}")
            return text

    def scrub_pii(self, data: Union[Dict[str, Any], List[Any], str]) -> Union[Dict[str, Any], List[Any], str]:
        """
        Recursively walks dicts/lists/strings to scrub everything.
        """
        if not PRESIDIO_AVAILABLE or not self.analyzer or not self.anonymizer:
            return data
            
        if isinstance(data, str):
            return self.scrub_text(data)
        elif isinstance(data, list):
            return [self.scrub_pii(item) for item in data]
        elif isinstance(data, dict):
            return {k: self.scrub_pii(v) for k, v in data.items()}
        else:
            return data


# Global singleton
_privacy_guard = None

def get_privacy_guard() -> PrivacyGuard:
    """Get singleton privacy guard instance."""
    global _privacy_guard
    if _privacy_guard is None:
        _privacy_guard = PrivacyGuard()
    return _privacy_guard
