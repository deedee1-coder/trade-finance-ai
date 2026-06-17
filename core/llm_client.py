import json
import re
import openai
from core.config import settings

_client: openai.OpenAI | None = None


def get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        _client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def call_claude(system: str, user: str, max_tokens: int | None = None) -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=settings.MODEL,
        max_tokens=max_tokens or settings.MAX_TOKENS,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content


def parse_json_response(text: str) -> dict:
    """Extract and parse JSON from a Claude response that may include markdown fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError(f"No JSON found in response: {text[:300]}")
