# chatbot/__init__.py
"""
chatbot SDK — Conversational investor onboarding chatbot
"""

from chatbot.client import chatbotClient
from chatbot.storage.local_storage import LocalStorage
from chatbot.storage.s3_storage import S3Storage
from chatbot.config.form_config import FormConfig
from chatbot.pdf.interface import PDFFillerInterface
from chatbot.limits.rate_limiter import RateLimiter, RateLimitConfig, RateLimitExceeded

__version__ = "0.1.0"
__all__ = [
    "chatbotClient",
    "LocalStorage",
    "S3Storage",
    "FormConfig",
    "PDFFillerInterface",
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitExceeded",
]
