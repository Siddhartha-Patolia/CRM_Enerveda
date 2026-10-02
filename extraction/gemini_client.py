import base64
import re
from dataclasses import dataclass
from typing import Optional, Tuple

import httpx
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import GoogleModelNotFoundError, GoogleRateLimitError
from pydantic import BaseModel, Field, field_validator

import config

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ExtractedContact(BaseModel):
    name: Optional[str] = Field(default=None, description="Full name of the individual on the card, if one is clearly present.")
    company: Optional[str] = Field(default=None, description="Company or organization name, if present.")
    phone: Optional[str] = Field(default=None, description="Primary phone number as printed, if present.")
    email: Optional[str] = Field(default=None, description="Email address, if present.")

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value and not _EMAIL_RE.match(value):
            return None
        return value

    def is_empty(self) -> bool:
        return not any([self.name, self.company, self.phone, self.email])


class ExtractionError(Exception):
    """Base class for a failed Gemini call — a technical/system problem, not a bad photo."""


class ExtractionTimeoutError(ExtractionError):
    """The Gemini request didn't complete within the configured timeout."""


class RateLimitExceededError(ExtractionError):
    """The Gemini API key has hit its rate limit/quota."""


class ModelUnavailableError(ExtractionError):
    """The configured Gemini model name is invalid or no longer available."""


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


llm = ChatGoogleGenerativeAI(
    model=config.MODEL,
    google_api_key=config.GEMINI_API_KEY,
    timeout=config.GEMINI_TIMEOUT_SECONDS,
    temperature=0,
)
structured_llm = llm.with_structured_output(ExtractedContact, include_raw=True)


def extract(image_bytes: bytes, mime_type: str = "image/jpeg") -> Tuple[ExtractedContact, TokenUsage]:
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    message = HumanMessage(
        content=[
            {"type": "text", "text": config.PROMPT_TEXT},
            {"type": "image_url", "image_url": f"data:{mime_type};base64,{b64_image}"},
        ]
    )

    try:
        result = structured_llm.invoke([message])
    except httpx.TimeoutException as exc:
        raise ExtractionTimeoutError(f"Gemini request timed out: {exc}") from exc
    except GoogleRateLimitError as exc:
        raise RateLimitExceededError(f"Gemini rate limit hit: {exc}") from exc
    except GoogleModelNotFoundError as exc:
        raise ModelUnavailableError(f"Gemini model unavailable: {exc}") from exc
    except Exception as exc:
        raise ExtractionError(f"Request failed: {exc}") from exc

    if result["parsing_error"] is not None:
        raise ExtractionError(f"Failed to parse Gemini response: {result['parsing_error']}")

    usage = result["raw"].usage_metadata or {}
    token_usage = TokenUsage(
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
    )
    return result["parsed"], token_usage
