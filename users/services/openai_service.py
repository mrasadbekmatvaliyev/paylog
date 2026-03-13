from django.conf import settings
from openai import OpenAI


class OpenAIServiceError(Exception):
    pass


def get_ai_reply(message: str) -> str:
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        raise OpenAIServiceError("OPENAI_API_KEY is not configured in settings.py")

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model="gpt-4o-mini",
            input=message,
        )
        reply = response.output_text.strip()
        if not reply:
            raise OpenAIServiceError("Empty response from OpenAI")
        return reply
    except OpenAIServiceError:
        raise
    except Exception as exc:
        raise OpenAIServiceError(str(exc)) from exc
