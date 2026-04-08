import logging
import os

from openai import APIConnectionError
from openai import APIError
from openai import APITimeoutError
from openai import AuthenticationError
from openai import OpenAI


logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    pass


class OpenAICompatibleAIService:
    def __init__(self, api_key=None, model=None, base_url=None, timeout=30.0):
        self.api_key = api_key or os.getenv("AI_API_KEY", "")
        self.model = model or os.getenv("AI_MODEL", "")
        self.base_url = base_url or os.getenv("AI_BASE_URL", "")
        self.timeout = timeout

    def _client(self):
        kwargs = {
            "api_key": self.api_key,
            "timeout": self.timeout,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return OpenAI(**kwargs)

    def generate_reply(self, messages):
        if not self.api_key:
            raise AIServiceError("AI_API_KEY is not configured.")
        if not self.model:
            raise AIServiceError("AI_MODEL is not configured.")

        try:
            response = self._client().chat.completions.create(
                model=self.model,
                messages=messages,
            )
        except (AuthenticationError, APITimeoutError, APIConnectionError, APIError) as exc:
            logger.exception("AI service request failed")
            raise AIServiceError("AI service request failed.") from exc

        if not response.choices:
            raise AIServiceError("AI service returned no choices.")

        content = response.choices[0].message.content
        text = ""

        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    part = item.get("text")
                else:
                    part = getattr(item, "text", None)
                if part:
                    parts.append(part)
            text = "".join(parts)

        cleaned = text.strip()
        if not cleaned:
            raise AIServiceError("AI service returned empty response.")

        return cleaned
