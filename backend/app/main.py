import os
import tempfile
from datetime import date

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

load_dotenv()

from app.earth_engine import get_satellite_spectral_data
from app.gemini_engine import analyze_crop_damage_visual
from app.guardrails import execute_loss_audit
from app.schemas import ClaimDossierResponse

app = FastAPI(title="BhoomiDrishti Evidence Prototype", version="1.0.0")
origins = [value.strip() for value in os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",") if value.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["*"])


@app.get("/health")
def health_status():
    return {"status": "operational", "system": "BhoomiDrishti evidence prototype",
            "gemini_configured": bool(os.getenv("GEMINI_API_KEY"))}


@app.post("/api/v1/claims/process", response_model=ClaimDossierResponse)
async def process_crop_claim(latitude: float = Form(...), longitude: float = Form(...),
                             event_date: str = Form(...), context_notes: str = Form(""),
                             image: UploadFile = File(...)):
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=422, detail="Latitude/longitude are outside WGS84 bounds.")
    try:
        parsed_date = date.fromisoformat(event_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="event_date must use YYYY-MM-DD format.") from None
    if parsed_date > date.today():
        raise HTTPException(status_code=422, detail="event_date cannot be in the future.")
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP field image.")
    raw = await image.read(12 * 1024 * 1024 + 1)
    if not raw or len(raw) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be between 1 byte and 12 MB.")

    suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[image.content_type]
    path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="bhoomi-", suffix=suffix, delete=False) as f:
            f.write(raw)
            path = f.name
        # Run network-bound synchronous SDKs outside the async event loop.
        visual = await run_in_threadpool(analyze_crop_damage_visual, path, context_notes)
        spectral = await run_in_threadpool(get_satellite_spectral_data, latitude, longitude, parsed_date.isoformat())
        return execute_loss_audit(latitude, longitude, visual, spectral)
    except RuntimeError as exc:
        if "GEMINI_API_KEY" in str(exc):
            raise HTTPException(status_code=503, detail="Gemini is not configured. Set GEMINI_API_KEY in backend/.env.") from None
        raise HTTPException(status_code=502, detail="The visual analysis provider did not return a usable result.") from None
    except Exception:
        raise HTTPException(status_code=502, detail="The evidence analysis could not be completed. Check backend provider configuration and logs.") from None
    finally:
        if path and os.path.exists(path):
            os.remove(path)
