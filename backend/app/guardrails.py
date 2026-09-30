import hashlib
import json
import uuid
from datetime import datetime, timezone

from app.schemas import GeminiVisualAssessment, SatelliteSpectralSummary, ClaimDossierResponse


def execute_loss_audit(lat: float, lon: float, visual: GeminiVisualAssessment,
                       spectral: SatelliteSpectralSummary, transcription: str = "") -> ClaimDossierResponse:
# Create a traceable evidence summary. This prototype does not approve claims or payouts.
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not visual.valid_agricultural_sample:
        verdict = "HUMAN_REVIEW_INVALID_OR_NON_AGRICULTURAL_IMAGE"
        crop = "UNKNOWN"
        phenotype = "UNCONFIRMED"
        visual_loss = max(0.0, min(100.0, visual.estimated_loss_percentage))
        estimate = None
        basis = "No loss estimate; submitted image was not identified as an agricultural sample."
        guidance = "Please provide a clear field image. A reviewer should confirm the evidence."
    else:
        verdict = "HUMAN_REVIEW_REQUIRED"
        crop = visual.identified_crop_type
        phenotype = visual.damage_phenotype
        visual_loss = round(visual.estimated_loss_percentage, 2)
        guidance = visual.salvage_advisory.immediate_action
        if spectral.source == "earth_engine" and spectral.delta_ndvi is not None:
            normalized_spectral_pct = min(100.0, max(0.0, spectral.delta_ndvi / 0.35 * 100.0))
            estimate = round(0.60 * visual_loss + 0.40 * normalized_spectral_pct, 2)
            basis = "Prototype evidence-fusion estimate (60% visual estimate + 40% normalized NDVI change); not an official formula."
        else:
            estimate = None
            basis = "Visual model estimate only; satellite evidence unavailable, so no fused loss estimate was calculated."

    record = {
        "claim_id": f"BD-{uuid.uuid4().hex[:12].upper()}", "timestamp": timestamp,
        "latitude": lat, "longitude": lon, "crop_type": crop,
        "damage_phenotype": phenotype, "visual_loss_percentage": visual_loss,
        "satellite_source": spectral.source, "pre_event_ndvi": spectral.pre_event_ndvi,
        "post_event_ndvi": spectral.post_event_ndvi, "satellite_ndvi_delta": spectral.delta_ndvi,
        "computed_final_loss_percentage": estimate, "estimate_basis": basis,
        "audit_verdict": verdict, "salvage_guidance": guidance,
        "transcribed_context": transcription or None, "evidence_note": spectral.message,
    }
    digest = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return ClaimDossierResponse(**record, tamper_hash=digest)
