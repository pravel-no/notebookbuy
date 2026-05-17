"""Gemini AI service for laptop spec extraction and grounded web search."""
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from google import genai
from google.genai import types

from app_config import (
    GEMINI_API_KEY,
    GEMINI_MAX_RETRIES,
    GEMINI_MAX_WORKERS,
    GEMINI_MODEL,
    GEMINI_REQUEST_DELAY_SEC,
    GEMINI_SEARCH_DELAY_SEC,
)
from retry_utils import call_with_retry


log = logging.getLogger(__name__)

class AIService:
    """Wraps Google Gemini for structured spec extraction and Google Search tool."""

    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
        self.schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "cpu": types.Schema(type=types.Type.STRING),
                "gpu": types.Schema(type=types.Type.STRING),
                "ram": types.Schema(type=types.Type.INTEGER),
                "ssd": types.Schema(type=types.Type.INTEGER),
                "is_broken": types.Schema(type=types.Type.BOOLEAN),
            },
            required=["cpu", "gpu", "ram", "ssd", "is_broken"]
        )
        self.system_prompt = (
            "Extract laptop specs accurately. cpu: full model (e.g. 'Intel Core i7-12700H'). "
            "gpu: model or 'integrated'. ram/ssd: GB as integers. is_broken: true if parts/broken."
        )

    def extract_specs(self, ads_list: list[dict]) -> list[dict]:
        if not self.client:
            log.warning("Skipping AI extraction because GEMINI_API_KEY is not configured")
            return []

        def process_one(ad: dict) -> dict | None:
            try:
                content = f"Title: {ad['title']}\nDescription: {ad['text'][:2000]}"

                def _call():
                    return self.client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=[content],
                        config=types.GenerateContentConfig(
                            system_instruction=self.system_prompt,
                            response_mime_type="application/json",
                            response_schema=self.schema,
                            temperature=0.0,
                        ),
                    )

                response = call_with_retry(
                    _call,
                    max_retries=GEMINI_MAX_RETRIES,
                    base_delay_sec=GEMINI_REQUEST_DELAY_SEC or 1.0,
                    label=f"extract_specs:{ad['id']}",
                )
                if GEMINI_REQUEST_DELAY_SEC > 0:
                    time.sleep(GEMINI_REQUEST_DELAY_SEC)
                data = json.loads(response.text)
                data["id"] = ad["id"]
                return data
            except Exception as e:
                log.warning(f"AI failed for {ad['id']}: {e}")
                return None

        results = []
        with ThreadPoolExecutor(max_workers=GEMINI_MAX_WORKERS) as executor:
            futures = [executor.submit(process_one, ad) for ad in ads_list]
            for future in as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)
        return results

    def google_search_json(self, prompt: str) -> dict[str, Any]:
        if not self.client:
            return {}

        try:
            resp = call_with_retry(
                lambda: self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.0,
                    ),
                ),
                max_retries=GEMINI_MAX_RETRIES,
                base_delay_sec=GEMINI_SEARCH_DELAY_SEC or 1.0,
                label="google_search_json",
            )
            text = resp.text
            decoder = json.JSONDecoder()
            start = text.find("{")
            if start != -1:
                obj, _ = decoder.raw_decode(text[start:])
                if isinstance(obj, dict):
                    return obj
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            log.warning(f"Search tool error: {e}")
        return {}
