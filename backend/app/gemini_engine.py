import base64
import os
import time

import httpx
from PIL import Image

from app.schemas import GeminiVisualAssessment


_VISUAL_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "valid_agricultural_sample": {"type": "BOOLEAN"},
        "identified_crop_type": {"type": "STRING"},
        "crop_growth_stage": {"type": "STRING"},
        "damage_phenotype": {"type": "STRING"},
        "crop_lodging_percentage": {"type": "NUMBER"},
        "inundation_severity": {"type": "STRING"},
        "estimated_loss_percentage": {"type": "NUMBER"},
        "confidence_score": {"type": "NUMBER"},
        "audit_notes": {"type": "STRING"},
        "salvage_advisory": {
            "type": "OBJECT",
            "properties": {
                "immediate_action": {"type": "STRING"},
                "drainage_required": {"type": "BOOLEAN"},
                "fungicide_spray_recommended": {"type": "BOOLEAN"},
            },
            "required": ["immediate_action", "drainage_required", "fungicide_spray_recommended"],
        },
    },
    "required": [
        "valid_agricultural_sample", "identified_crop_type", "crop_growth_stage",
        "damage_phenotype", "crop_lodging_percentage", "inundation_severity",
        "estimated_loss_percentage", "confidence_score", "audit_notes", "salvage_advisory",
    ],
}


def _generate(parts: list[dict], response_schema: dict | None = None) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    config = {"temperature": 0.1}
    if response_schema:
        config.update({"responseMimeType": "application/json", "responseSchema": response_schema})
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    for attempt in range(3):
        try:
            response = httpx.post(
                url,
                headers={"x-goog-api-key": key},
                json={
                    "systemInstruction": {"parts": [{"text": "Describe visible crop condition cautiously for human review. Do not claim official status, insurance eligibility, or certainty."}]},
                    "contents": [{"role": "user", "parts": parts}],
                    "generationConfig": config,
                },
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()
            break
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status not in {408, 429, 500, 502, 503, 504} or attempt == 2:
                raise RuntimeError(f"Gemini API returned HTTP {status}") from None
            time.sleep(2 ** attempt)
        except httpx.HTTPError:
            if attempt == 2:
                raise RuntimeError("Gemini API could not be reached") from None
            time.sleep(2 ** attempt)
    try:
        return "".join(part["text"] for part in payload["candidates"][0]["content"]["parts"] if "text" in part)
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Gemini returned no usable text candidate") from None


def analyze_crop_damage_visual(image_path: str, context_notes: str = "") -> GeminiVisualAssessment:
    """Return a schema-constrained visual description, not an official loss determination."""
    with Image.open(image_path) as image:
        image.load()
        mime = Image.MIME.get(image.format or "")
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            raise RuntimeError("Uploaded image format is unsupported")
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("ascii")
    prompt = (
        "Describe visible crop damage and uncertainty. Treat farmer context as unverified. "
        f"Farmer-provided context: {context_notes}"
    )
    result = _generate(
        [{"inlineData": {"mimeType": mime, "data": encoded}}, {"text": prompt}],
        response_schema=_VISUAL_RESPONSE_SCHEMA,
    )
    return GeminiVisualAssessment.model_validate_json(result)


def transcribe_vernacular_voice(audio_path: str) -> str:
    """Optional audio path retained from the supplied guide; there is no audio control in the UI."""
    extension = os.path.splitext(audio_path)[1].lower()
    mime = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".webm": "audio/webm"}.get(extension)
    if not mime:
        raise RuntimeError("Audio format is unsupported")
    with open(audio_path, "rb") as audio:
        encoded = base64.b64encode(audio.read()).decode("ascii")
    return _generate([
        {"inlineData": {"mimeType": mime, "data": encoded}},
        {"text": "Transcribe and briefly summarize this farmer statement in English. Mark uncertain words."},
    ])
