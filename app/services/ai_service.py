"""
Wraps the Gemini API (free tier, no credit card) for the two AI-driven features:
multilingual auto-cataloging and the AI chat assistant. Falls back to a simple
rule-based stub if GEMINI_API_KEY isn't set, so the app still runs end-to-end.
"""

import json
import os
from typing import Optional

import google.generativeai as genai

from app.config import settings

MODEL = os.getenv("RANGREZ_AI_MODEL", "gemini-2.5-flash")
_configured = False


def _get_model() -> Optional["genai.GenerativeModel"]:
    global _configured
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    if not _configured:
        genai.configure(api_key=api_key)
        _configured = True
    return genai.GenerativeModel(MODEL)


CATALOG_SYSTEM_PROMPT = """You are Rangrez's multilingual product-cataloging assistant for Indian artisans.
An artisan describes their handmade craft by voice or text, often in Hindi or another
Indian regional language, sometimes mixed with English.

Given their raw description, produce a JSON object with exactly these fields:
{
  "detected_language": "<ISO 639-1 code of the language the artisan spoke in, e.g. hi, en, bn>",
  "craft_category": "<short category, e.g. 'Embroidered Textile', 'Wood Carving', 'Pottery', 'Block Print'>",
  "title_en": "<a clean, SEO-friendly English product title, under 12 words>",
  "title_native": "<the same title translated back into the artisan's own language>",
  "description_en": "<a polished English product description for an e-commerce/GeM/ONDC listing, 2-4 sentences>",
  "description_native": "<the same description in the artisan's own language>",
  "tags": ["<3 to 6 short search tags>"]
}

Only output the JSON object, nothing else — no markdown fences, no preamble."""

CHAT_SYSTEM_PROMPT = """You are Rangrez, a warm, practical virtual business manager for Indian artisans
and weavers selling through GeM, ONDC, and institutional buyers. Artisans may write in
Hindi, English, or a mix. Reply in the same language/script they used.

Respond with a JSON object with exactly these fields:
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
    model = _get_model()
    if model is None:
        return _stub_catalog(spoken_description)

    prompt = spoken_description
    if language_hint:
        prompt += f"\n\n(Artisan indicated their language is: {language_hint})"

    try:
        response = model.generate_content(
            [CATALOG_SYSTEM_PROMPT, prompt],
            generation_config={"max_output_tokens": 800},
        )
        return _extract_json(response.text)
    except Exception:
        return _stub_catalog(spoken_description)


def chat_reply(message: str, language_hint: Optional[str] = None) -> dict:
    model = _get_model()
    if model is None:
        return _stub_chat(message)

    prompt = message
    if language_hint:
        prompt += f"\n\n(Artisan indicated their language is: {language_hint})"

    try:
        response = model.generate_content(
            [CHAT_SYSTEM_PROMPT, prompt],
            generation_config={"max_output_tokens": 400},
        )
        return _extract_json(response.text)
    except Exception:
        return _stub_chat(message)


# ---------------------------------------------------------------------------
# Rule-based fallbacks (used only when no API key is configured)
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
