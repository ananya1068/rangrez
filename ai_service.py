"""
Wraps the Anthropic API for the two AI-driven features in the frontend:

  1. Multilingual Auto-Cataloger — turn a spoken/typed regional-language product
     description into an English + native-language listing (title, description, tags).
  2. AI Chat / virtual business manager — answer artisan questions (pricing, general
     "how do I ...") in whichever language they wrote in.

If ANTHROPIC_API_KEY isn't set (e.g. running the demo without a key yet), both
functions fall back to a simple rule-based stub so the rest of the app still works
end-to-end — useful for local dev before wiring up the key.
"""

import json
import os
from typing import Optional

from anthropic import Anthropic

from app.config import settings

_client: Optional[Anthropic] = None
MODEL = os.getenv("RANGREZ_AI_MODEL", "claude-sonnet-5")


def _get_client() -> Optional[Anthropic]:
    global _client
    if not settings.ANTHROPIC_API_KEY:
        return None
    if _client is None:
        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


CATALOG_SYSTEM_PROMPT = """You are Rangrez's multilingual product-cataloging assistant for Indian artisans.
An artisan describes their handmade craft by voice or text, often in Hindi or another
Indian regional language, sometimes mixed with English.

Given their raw description, produce a JSON object with exactly these fields:
{
  "detected_language": "<ISO 639-1 code of the language the artisan spoke in, e.g. hi, en, bn>",
  "craft_category": "<short category, e.g. 'Embroidered Textile', 'Wood Carving', 'Pottery', 'Block Print'>",
  "title_en": "<a clean, SEO-friendly English product title, under 12 words>",
  "title_native": "<the same title translated back into the artisan's own language>",
  "description_en": "<a polished English product description for an e-commerce/GeM/ONDC listing, 2-4 sentences, highlighting materials, technique, and origin>",
  "description_native": "<the same description in the artisan's own language>",
  "tags": ["<3 to 6 short search tags>"]
}

Only output the JSON object, nothing else — no markdown fences, no preamble."""

CHAT_SYSTEM_PROMPT = """You are Rangrez, a warm, practical virtual business manager for Indian artisans
and weavers selling through GeM, ONDC, and institutional buyers. Artisans may write in
Hindi, English, or a mix. Reply in the same language/script they used.

Classify the artisan's message and respond with a JSON object with exactly these fields:
{
  "detected_intent": "<one of: pricing_question, catalog_request, general>",
  "reply_language": "<ISO 639-1 code you replied in>",
  "reply": "<your reply text, 1-3 short sentences, friendly and concrete>"
}

Only output the JSON object, nothing else."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def generate_catalog_listing(spoken_description: str, language_hint: Optional[str] = None) -> dict:
    client = _get_client()
    if client is None:
        return _stub_catalog(spoken_description)

    user_content = spoken_description
    if language_hint:
        user_content += f"\n\n(Artisan indicated their language is: {language_hint})"

    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=CATALOG_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text")
    try:
        return _extract_json(raw_text)
    except (json.JSONDecodeError, ValueError):
        return _stub_catalog(spoken_description)


def chat_reply(message: str, language_hint: Optional[str] = None) -> dict:
    client = _get_client()
    if client is None:
        return _stub_chat(message)

    user_content = message
    if language_hint:
        user_content += f"\n\n(Artisan indicated their language is: {language_hint})"

    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=CHAT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text")
    try:
        return _extract_json(raw_text)
    except (json.JSONDecodeError, ValueError):
        return _stub_chat(message)


# ---------------------------------------------------------------------------
# Rule-based fallbacks (used only when no API key is configured yet)
# ---------------------------------------------------------------------------

_PRICE_KEYWORDS = ["price", "cost", "kimat", "keemat", "\u0915\u0940\u092e\u0924", "\u092d\u093e\u0935", "rate"]


def _stub_catalog(spoken_description: str) -> dict:
    return {
        "detected_language": "hi" if any(ord(ch) > 127 for ch in spoken_description) else "en",
        "craft_category": "General handicraft",
        "title_en": spoken_description[:60].strip().title() or "Handmade Craft Item",
        "title_native": spoken_description[:60].strip(),
        "description_en": (
            f"A handmade craft piece: {spoken_description.strip()}. "
            "Crafted using traditional techniques passed down through generations."
        ),
        "description_native": spoken_description.strip(),
        "tags": ["handmade", "artisan", "traditional-craft"],
    }


def _stub_chat(message: str) -> dict:
    is_pricing = any(k.lower() in message.lower() for k in _PRICE_KEYWORDS)
    is_hindi = any(ord(ch) > 127 for ch in message)
    if is_pricing:
        reply = (
            "\u0915\u0943\u092a\u092f\u093e \u0905\u092a\u0928\u093e \u0915\u094d\u0937\u0947\u0924\u094d\u0930 "
            "\u0914\u0930 \u0938\u093e\u092e\u0917\u094d\u0930\u0940 \u0932\u093e\u0917\u0924 \u092c\u0924\u093e\u090f\u0902, "
            "\u092e\u0948\u0902 \u0905\u092d\u0940 \u0938\u0942\u091a\u093f\u0924 \u092e\u0942\u0932\u094d\u092f \u0928\u093f\u0915\u093e\u0932\u0924\u093e "
            "\u0939\u0942\u0902\u0964"
            if is_hindi
            else "Tell me your region and raw material cost and I'll suggest a fair price range."
        )
        return {"detected_intent": "pricing_question", "reply_language": "hi" if is_hindi else "en", "reply": reply}
    return {
        "detected_intent": "general",
        "reply_language": "hi" if is_hindi else "en",
        "reply": (
            "\u0906\u092a\u0915\u0940 \u091c\u093e\u0928\u0915\u093e\u0930\u0940 \u0926\u0930\u094d\u091c \u0915\u0930 "
            "\u0932\u0940 \u0917\u0908 \u0939\u0948\u0964"
            if is_hindi
            else "Got it — tell me more about your craft and I can help catalog or price it."
        ),
    }
